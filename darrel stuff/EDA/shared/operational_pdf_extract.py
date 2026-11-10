"""Extract only declared case pages, retaining source/page hashes; no instructions are executed from PDFs."""
from pathlib import Path
import argparse
import gc
import hashlib
import json


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def extract(config_path,output,sample=False):
    from pypdf import PdfReader,__version__
    config=json.loads(config_path.read_text());root=Path(config['external_root'])/'keep';selection={}
    for case in config['cases']:selection.setdefault(case['file'],set()).update(case['pages'])
    if sample:
        names=['A16_MissionReport.pdf','LMA790-3-LM10-ApolloOperationsHandbookLunarModuleLM10AndSubsequent-Volume1-SubsystemsData.pdf']
        selection={name:selection[name] for name in names}
    rows=[]
    for name,pages in selection.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()):raise ValueError('PDF path escapes selected library')
        sha=digest(path);reader=PdfReader(str(path));texts=[]
        for page in sorted(pages):
            if not 1<=page<=len(reader.pages):raise ValueError('Requested PDF page outside document')
            text=reader.pages[page-1].extract_text()
            texts.append({'pdf_page':page,'text':text,'text_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
                'text_characters':len(text),'review_scope':'declared page text; not full-document/image/table review'})
        if digest(path)!=sha:raise ValueError('PDF changed during extraction')
        rows.append({'file':name,'source_path':str(path),'source_sha256':sha,'total_pdf_pages':len(reader.pages),'pages':texts})
        del reader;gc.collect();print('Extracted declared pages:',name,flush=True)
    result={'schema':1,'sample':sample,'extractor':'pypdf '+__version__,'case_config_sha256':digest(config_path),'documents':rows}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('config',type=Path);p.add_argument('output',type=Path);p.add_argument('--sample',action='store_true')
    args=p.parse_args();extract(args.config,args.output,args.sample)
