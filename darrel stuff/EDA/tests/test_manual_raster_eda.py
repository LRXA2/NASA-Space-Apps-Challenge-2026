from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
from rasterio.transform import from_origin
import rasterio

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "shared"), str(Path(__file__).resolve().parents[1] / "Moon/Stage3_Requirements"), str(Path(__file__).resolve().parents[3])]
from manual_raster_eda import (SPECIAL_BITS, classify_pixels, radar_indices, radar_preview,
                               sample_radar, sample_shadow, attach_pixels, regional_summary,
                               relationship_tables, distribution, shadow_definition, radar_definition)


class ManualRasterTests(unittest.TestCase):
    def test_exact_isis_bits_and_signed_values(self):
        raw = np.array([*SPECIAL_BITS.values()], dtype='<u4').view('<f4')
        values = np.r_[raw, np.array([np.nan, np.inf, -1, 0, 2], dtype='<f4')]
        self.assertEqual(classify_pixels(values).tolist(), [*SPECIAL_BITS, 'nonfinite', 'nonfinite', 'valid', 'valid', 'valid'])

    def test_ordinary_declared_nodata_is_separate(self):
        self.assertEqual(classify_pixels(np.array([-99, -1, 0], dtype='float32'), -99).tolist(), ['declared_nd', 'valid', 'valid'])

    def test_special_pixel_categories_survive_default_csv_roundtrip(self):
        import io
        raw=np.array(list(SPECIAL_BITS.values()),dtype='<u4').view('<f4')
        frame=pd.DataFrame({'pixel_status':classify_pixels(raw)})
        restored=pd.read_csv(io.StringIO(frame.to_csv(index=False)))
        self.assertFalse(restored.pixel_status.isna().any())
        self.assertEqual(restored.pixel_status.tolist(),list(SPECIAL_BITS))

    def test_angular_pixel_centres_seam_and_poles(self):
        r, c, ok = radar_indices([-179.5, 179.5, 180, -180, np.nan, 0, 0],
                                  [89.5, -89.5, 0, 0, 0, -90, 90], 1)
        np.testing.assert_array_equal(r[:4], [0, 179, 90, 90])
        np.testing.assert_array_equal(c[:4], [0, 359, 0, 0])
        self.assertEqual(ok.tolist(), [True, True, True, True, False, False, False])

    def test_memmap_samples_and_preview_match_direct_values(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'a.img'
            original = np.arange(180*360, dtype='<f4').reshape(180, 360)
            original.tofile(path)
            meta = {'shape': [180,360], 'offset': 0, 'ppd': 1}
            values, r, c, valid = sample_radar(path, meta, [-179.5, 179.5], [89.5, -89.5])
            np.testing.assert_array_equal(values, original[r,c])
            np.testing.assert_array_equal(radar_preview(path, meta, 4), original[::4,::4])

    def context(self):
        return pd.DataFrame({'region': ['a']*3, **{n: [1.,2.,3.] for n in
            ['solar_visibility','earth_visibility','sky_view_sr','elevation_m','slope_deg']},
            'permanent_shadow': [0.,0.,1.]})

    def test_empty_support_is_nan_not_zero(self):
        f = attach_pixels(self.context(), np.full(3,np.nan,dtype='float32'), np.zeros(3,int), np.zeros(3,int), np.zeros(3,bool))
        result = regional_summary(f).iloc[0]
        self.assertEqual(result.analysis_centres,0)
        self.assertTrue(np.isnan(result['median']))
        unique, relation, contrasts = relationship_tables(f)
        self.assertTrue(unique.empty)
        self.assertTrue(relation.status.eq('insufficient_rows').all())
        self.assertTrue(contrasts['count'].eq(0).all())

    def test_negative_cpr_is_separate_not_implicitly_nodata(self):
        f = attach_pixels(self.context(), np.array([-1,0,2],dtype='float32'), np.arange(3), np.zeros(3,int), np.ones(3,bool), nonnegative=True)
        self.assertEqual(f.ordinary_pixel.sum(),3)
        self.assertEqual(f.nonnegative_screen.sum(),2)
        self.assertTrue(np.isnan(f.analysis_value.iloc[0]))
        self.assertEqual(regional_summary(f).negative_ordinary_pixels.iloc[0],1)

    def test_duplicate_source_pixel_is_one_record_and_mixed_masks_stay_unknown(self):
        f=attach_pixels(self.context(),np.array([1,1,1],dtype='float32'),np.zeros(3,int),np.zeros(3,int),np.ones(3,bool))
        unique, relations, contrasts=relationship_tables(f,minimum=2)
        self.assertEqual(len(unique),1)
        self.assertTrue(np.isnan(unique.permanent_shadow.iloc[0]))
        self.assertTrue(relations.status.eq('insufficient_rows').all())
        self.assertEqual(contrasts.loc[contrasts.parent_shadow_context.eq('mixed_or_unknown_parent_mask'),'count'].iloc[0],1)

    def test_shadow_grouped_native_reads_match_direct_grid(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'a.tif'
            array=np.arange(100,dtype='float32').reshape(10,10)
            transform=from_origin(-5,5,1,1)
            with rasterio.open(path,'w',driver='GTiff',height=10,width=10,count=1,dtype='float32',
                               crs='+proj=longlat +R=1737400',transform=transform,nodata=-99) as out:
                out.write(array,1)
            values, r,c,inside,nodata=sample_shadow(path,np.array([-4.5,4.5,50]),np.array([4.5,-4.5,0]))
            np.testing.assert_array_equal(values[:2],[0,99])
            self.assertFalse(inside[-1])
            self.assertTrue(np.isnan(values[-1]))

    def test_distribution_retains_zero_and_empty_status(self):
        self.assertEqual(distribution([0,1,np.nan])['count'],2)
        self.assertTrue(np.isnan(distribution([])['median']))

    def test_shadow_native_variant_b_label_validation_and_wrong_size(self):
        with tempfile.TemporaryDirectory() as t:
            image=Path(t)/'M013049982S_map_raw.tif'
            with rasterio.open(image,'w',driver='GTiff',height=3,width=4,count=1,dtype='float32',
                               crs='+proj=stere +lat_0=-90 +lat_ts=-88.12 +lon_0=20.56 +R=1737400 +units=m',
                               transform=from_origin(-4,7,1,1)) as out:
                out.write(np.ones((3,4),dtype='float32'),1)
            values={'logical_identifier':'urn:test:m013049982s_map_raw','file_name':image.name,
                    'file_size':image.stat().st_size,'upperleft_corner_x':-4,'upperleft_corner_y':7,
                    'pixel_resolution_x':1,'pixel_resolution_y':1,'a_axis_radius':1737400,
                    'latitude_of_projection_origin':-88.12,'longitude_of_central_meridian':20.56}
            label=Path(t)/'label.xml.txt'
            def save():label.write_text('<Product_Browse>'+''.join(f'<{k}>{v}</{k}>' for k,v in values.items())+'</Product_Browse>')
            save();meta=shadow_definition(label,image)
            self.assertEqual(meta['shape'],[3,4])
            values['file_size']+=1;save()
            with self.assertRaises(ValueError):shadow_definition(label,image)

    def test_radar_label_agreement_bytes_and_unrepresentable_missing_constant(self):
        with tempfile.TemporaryDirectory() as t:
            image=Path(t)/'global_cpr_128ppd_simp_0c.img'
            np.ones((180,360),dtype='<f4').tofile(image)
            detached=Path(t)/'a.lbl'
            detached.write_text('LINES = 180\nLINE_SAMPLES = 360\nSAMPLE_BITS = 32\nBANDS = 1\nSAMPLE_TYPE = PC_REAL\nSCALING_FACTOR = 1\nOFFSET = 0\nMAP_RESOLUTION = 1\n')
            r=1737400.;scale=r*np.pi/180
            fields={'logical_identifier':'urn:test:global_cpr_128ppd_simp_0c',
                    'pixel_scale_x':1,'pixel_scale_y':1,'west_bounding_coordinate':-180,'east_bounding_coordinate':180,
                    'north_bounding_coordinate':90,'south_bounding_coordinate':-90,'a_axis_radius':1737.4,
                    'pixel_resolution_x':scale,'pixel_resolution_y':scale,'upperleft_corner_x':-r*np.pi,'upperleft_corner_y':r*np.pi/2}
            label=Path(t)/'a.xml'
            label.write_text('<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1">'+
                ''.join(f'<{k}>{v}</{k}>' for k,v in fields.items())+
                f'<File_Area_Observational><File><file_name>{image.name}</file_name></File><Array_2D_Image><offset>0</offset>'+
                '<Element_Array><data_type>IEEE754LSBSingle</data_type></Element_Array>'+
                '<Axis_Array><axis_name>Line</axis_name><elements>180</elements></Axis_Array>'+
                '<Axis_Array><axis_name>Sample</axis_name><elements>360</elements></Axis_Array>'+
                '<Special_Constants><missing_constant>-1.7976931e308</missing_constant></Special_Constants>'+
                '</Array_2D_Image></File_Area_Observational></Product_Observational>')
            meta=radar_definition(label,detached,image)
            self.assertFalse(meta['label_missing_representable_float32'])
            image.write_bytes(b'short')
            with self.assertRaises(ValueError):radar_definition(label,detached,image)


if __name__ == '__main__':
    unittest.main()
