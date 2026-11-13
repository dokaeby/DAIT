import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const M='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules';
const req=createRequire(path.join(M,'__runtime__.cjs'));
const {PresentationFile,FileBlob}=await import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
const p=await PresentationFile.importPptx(await FileBlob.load('C:/Users/Playdata/Desktop/DAIT_3팀_피치덱_10장_v2.pptx'));
const b='C:/DAIT/docs/pitch/.build';
await fs.writeFile(path.join(b,'source12.json'),JSON.stringify(p.toProto()));
for(let i=0;i<p.slides.items.length;i++){const blob=await p.export({slide:p.slides.items[i],format:'png',scale:.65});await fs.writeFile(path.join(b,`source12-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));}
console.log(JSON.stringify(p.help('slide.shapes',{search:'delete remove clear',include:['index','notes','examples'],maxChars:5000})));
console.log(JSON.stringify(p.help('slide.images',{search:'delete remove clear',include:['index','notes','examples'],maxChars:5000})));
console.log(JSON.stringify(p.help('presentation.slides',{search:'delete remove add',include:['index','notes','examples'],maxChars:5000})));
