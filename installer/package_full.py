"""Build private offline EXE from public source plus explicitly selected local resources."""
import argparse, hashlib, json, subprocess, tempfile, zipfile
from pathlib import Path
from package_update import build, release_version

def package(output, resources, prerequisites):
    root=Path(__file__).resolve().parent.parent
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    version=release_version(root)
    destination=output/f'SonMapPlus_V{version.replace(".","_")}_Full_Setup.exe'
    if destination.exists():raise FileExistsError(destination)
    allowed=['assets/TrichLucTT26 -ThanhTan.dgn','assets/Mau03CLBD.dgn','ThanhTanApp.mvba']
    for name in allowed:
        if not (resources/name).is_file():raise FileNotFoundError(name)
    required=['python-3.12.10-amd64.exe','wheels/shapely-2.0.7-cp312-cp312-win_amd64.whl','wheels/numpy-1.26.4-cp312-cp312-win_amd64.whl']
    for name in required:
        if not (prerequisites/name).is_file():raise FileNotFoundError(name)
    with tempfile.TemporaryDirectory(prefix='SonMap-build-',dir=output.parent) as temp:
        stage=Path(temp)
        update=build(stage,root)
        with zipfile.ZipFile(update) as package:
            package.extractall(stage/'bundle')
        bundle_root=stage/'bundle'
        manifest=[dict(file=name,sha256=hashlib.sha256((resources/name).read_bytes()).hexdigest()) for name in allowed]
        with zipfile.ZipFile(bundle_root/'resources.zip','w',zipfile.ZIP_DEFLATED) as z:
            for name in allowed:z.write(resources/name,name)
            z.writestr('resources-manifest.json',json.dumps(manifest,indent=2))
        bundle=stage/'bundle.zip'
        with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
            for path in bundle_root.iterdir():z.write(path,path.name)
            for name in required:z.write(prerequisites/name,'prerequisites/'+name)
        with zipfile.ZipFile(bundle) as z:
            if z.testzip():raise ValueError('Bundle CRC failure')
        source=(root/'installer/FullSetup.cs').read_text(encoding='utf-8').replace('BUNDLE_HASH',hashlib.sha256(bundle.read_bytes()).hexdigest()).replace('APP_VERSION',version)
        cs=stage/'FullSetup.cs';cs.write_text(source,encoding='utf-8-sig')
        compiler=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
        subprocess.run([str(compiler),'/nologo','/target:winexe','/platform:x64','/out:'+str(destination),'/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.IO.Compression.dll','/r:System.IO.Compression.FileSystem.dll','/resource:'+str(bundle)+',bundle.zip',str(cs)],check=True)
    checksum=hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.exe.sha256').write_text(checksum+'  '+destination.name+'\n',encoding='ascii')
    return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resources',type=Path,required=True)
    parser.add_argument('--prerequisites',type=Path,required=True)
    args=parser.parse_args()
    print(package(args.output,args.resources.resolve(),args.prerequisites.resolve()))
