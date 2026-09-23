import contextlib
import io
import json
import os
from pathlib import Path
import socketserver
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fetch_references as f
import index_scene_methods as indexer
import expand_ponder_manifest as expander


def zip_bytes(names=('sound.ogg',)):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        for name in names:z.writestr(name,b'fixture, not playable audio')
    return stream.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path=='/missing':self.send_error(404);return
        if self.path=='/redirect':
            self.send_response(302);self.send_header('Location','/code');self.end_headers();return
        if self.path=='/downgrade':
            self.send_response(302);self.send_header('Location','http://example.com/source');self.end_headers();return
        body,kind={
            '/code':(b'public class Reference {}\n','text/plain'),
            '/bad':(b'<html><title>Not source</title></html>','text/html'),
            '/large':(b'x'*200,'text/plain'),
            '/noclength':(b'x'*200,'text/plain'),
            '/zip':(zip_bytes(),'application/zip'),
            '/asset.zip':(zip_bytes(),'application/zip'),
            '/page':(b'<a href="/asset.zip">download</a>','text/html'),
        }.get(self.path,(b'', 'application/octet-stream'))
        self.send_response(200);self.send_header('Content-Type',kind)
        if self.path!='/noclength':self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=socketserver.TCPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_address[1]}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def entry(self,path='/code',kind='text',output='sample.txt',max_bytes=500):
        return {'id':'sample','url':self.base+path,'source_url':self.base+path,
                'output':output,'kind':kind,'max_bytes':max_bytes}
    def fetch(self,e,budget=1024):return f.fetch_one(e,self.root,f.Budget(budget),test_local_http=True)
    def test_real_local_text_transfer(self):
        result=self.fetch(self.entry())
        self.assertEqual(result['status'],'downloaded')
        self.assertEqual((self.root/'sample.txt').read_text(),'public class Reference {}\n')
        self.assertFalse(list(self.root.glob('*.part')))
    def test_real_local_zip_crc_and_inventory(self):
        result=self.fetch(self.entry('/zip','zip','asset.zip',2000),4096)
        self.assertTrue(result['validation']['zip_crc_ok'])
        self.assertEqual(result['validation']['members'][0]['name'],'sound.ogg')
        self.assertFalse((self.root/'sound.ogg').exists())
    def test_existing_file_preserved_without_network(self):
        (self.root/'sample.txt').write_text('existing')
        result=self.fetch(self.entry('/missing'))
        self.assertEqual(result['status'],'existing_not_overwritten')
        self.assertEqual((self.root/'sample.txt').read_text(),'existing')
    def test_html_rejected_and_part_removed(self):
        with self.assertRaises(f.FetchError):self.fetch(self.entry('/bad'))
        self.assertEqual(list(self.root.iterdir()),[])
    def test_budget_rejects_declared_size(self):
        with self.assertRaises(f.FetchError):self.fetch(self.entry('/large'),50)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_budget_rejects_stream_without_content_length(self):
        with self.assertRaises(f.FetchError):self.fetch(self.entry('/noclength'),50)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_404_does_not_leave_partial(self):
        with self.assertRaises(Exception):self.fetch(self.entry('/missing'))
        self.assertEqual(list(self.root.iterdir()),[])
    def test_http_only_for_loopback_test_mode(self):
        with self.assertRaises(f.FetchError):f.validate_url(self.base)
        f.validate_url(self.base,True)
        with self.assertRaises(f.FetchError):f.validate_url('http://example.com/a',True)
    def test_redirect_validated(self):
        self.assertEqual(self.fetch(self.entry('/redirect'))['status'],'downloaded')
    def test_redirect_to_external_http_rejected(self):
        with self.assertRaises(f.FetchError):self.fetch(self.entry('/downgrade'))
    def test_output_traversal_rejected(self):
        for path in ('../x','/absolute','C:/x','a\\b','a/../x','a//x','a./x'):
            with self.subTest(path=path),self.assertRaises(f.FetchError):f.target_path(self.root,path)
    def test_symlink_escape_rejected(self):
        outside=self.root/'outside';outside.mkdir()
        inside=self.root/'inside';inside.mkdir()
        (inside/'link').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(f.FetchError):f.target_path(inside,'link/file')
    def test_page_link_resolution(self):
        url=f.resolve_page_link('<a href="/files/a%20b.zip">x</a>','https://example.org/page','a b.zip',['example.org'])
        self.assertEqual(url,'https://example.org/files/a%20b.zip')
    def test_ambiguous_page_link_fails(self):
        with self.assertRaises(f.FetchError):
            f.resolve_page_link('<a href="/one/a.zip"></a><a href="/two/a.zip"></a>',
                                'https://example.org/page','a.zip',['example.org'])
    def test_page_resolution_and_download_end_to_end_local(self):
        e=self.entry('/page','zip','asset.zip',2000);e['url']=None
        e['resolver']={'type':'page_link','basename':'asset.zip','allowed_hosts':['127.0.0.1']}
        self.assertEqual(self.fetch(e,4096)['status'],'downloaded')
    def test_zip_traversal_rejected(self):
        p=self.root/'bad.zip';p.write_bytes(zip_bytes(('../escape',)))
        with self.assertRaises(f.FetchError):f.validate_payload(p,'zip')
    def test_zero_bytes_rejected(self):
        p=self.root/'zero';p.write_bytes(b'')
        with self.assertRaises(f.FetchError):f.validate_payload(p,'text')
    def test_dry_run_writes_nothing_and_makes_no_requests(self):
        m=self.root/'m.json';m.write_text(json.dumps({'schema_version':1,'items':[dict(self.entry(),group='test')]}))
        out=self.root/'dry'
        with contextlib.redirect_stdout(io.StringIO()):
            code=f.main(['--manifest',str(m),'--group','test','--dest',str(out)])
        self.assertEqual(code,0);self.assertFalse(out.exists())
    def test_actual_manifests_parse(self):
        for p in (f.KIT/'scripts/source_manifest.json',f.KIT/'skyboxes/manifest.json',f.KIT/'audio/manifest.json'):
            self.assertTrue(f.load_entries([p]))
    def test_unknown_selection_rejected(self):
        with self.assertRaises(f.FetchError):f.choose([self.entry()],[],['absent'])
    def test_license_auto_selection(self):
        e=dict(self.entry(),repo='A/B',group='code')
        lic=dict(self.entry(),id='lic',repo='A/B',group='license',upstream_path='LICENSE')
        self.assertEqual(len(f.choose([e,lic],['code'],[])),2)
    def test_method_indexer(self):
        p=self.root/'PistonScenes.java'
        p.write_text('class X {\n public static void movement(SceneBuilder b, SceneBuildingUtil u) {}\n}')
        result=indexer.inventory(self.root)
        self.assertEqual(result['count'],1);self.assertEqual(result['methods'][0]['line'],2)
    def test_full_ponder_tree_filter(self):
        tree={'truncated':False,'tree':[{'type':'blob','path':'LICENSE','size':100},
              {'type':'blob','path':expander.PREFIX+'api/Scene.java','size':150},
              {'type':'blob','path':'common/src/main/resources/assets/a.png','size':999}]}
        manifest=expander.convert_tree(tree)
        self.assertEqual(len(manifest['items']),2)
    def test_truncated_tree_rejected(self):
        with self.assertRaises(f.FetchError):expander.convert_tree({'truncated':True,'tree':[]})


if __name__=='__main__':unittest.main(verbosity=2)
