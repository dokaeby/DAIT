import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const MOD='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules';
process.env.RUNTIME_NODE_MODULES=MOD;
const req=createRequire(path.join(MOD,'__runtime__.cjs'));
const {PresentationFile,FileBlob}=await import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
const ROOT='C:/DAIT/docs/pitch',B=path.join(ROOT,'.build');
const SKILL='C:/Users/Playdata/.codex/plugins/cache/openai-primary-runtime/presentations/26.1112.11011/skills/presentations';
const p=await PresentationFile.importPptx(await FileBlob.load(path.join(ROOT,'output','DAIT_피치덱_10장.pptx')));
const s=p.slides.items[8];
const before=await p.export({slide:s,format:'png',scale:1});
await fs.writeFile(path.join(B,'team-before.png'),new Uint8Array(await before.arrayBuffer()));
const title=s.shapes.items.find(x=>Math.abs(x.position.top-52)<1);
title.text='3팀 소개와 역할 분담';
const labels=s.shapes.items.filter(x=>Math.abs(x.position.left-64)<1 && [199,345,491].some(y=>Math.abs(x.position.top-y)<1));
const bodies=s.shapes.items.filter(x=>Math.abs(x.position.left-374)<1);
const rules=s.shapes.items.filter(x=>x.position.height<=2);
if(labels.length!==3||bodies.length!==3||rules.length!==3)throw new Error('Unexpected source layout');
function style(shape,text,left,top,width,height,size,bold,color){shape.text=text;shape.position={left,top,width,height};shape.text.style={typeface:'Malgun Gothic',fontSize:size,bold,color,insets:0,autoFit:'none',wrap:'square',verticalAlignment:'top'};}
function add(){return s.shapes.add({geometry:'textbox',fill:'none',line:{fill:'none',width:0}});}
const rows=[
 ['양성훈 · 팀장','산출물 문서 작업\n작업물 관리 및 수정'],
 ['김지훈(A)','국내·해외 기사 요약 및 번역'],
 ['홍록기','회원가입·로그인, Supabase DB 연동\n구글 소셜 로그인 및 보안 처리'],
 ['조정한','설정 기능: 알림·카테고리 지정 및 메인화면 연동\n발표'],
 ['박수민','기획, 로그인·비로그인 메인화면\n설정화면 UI']
];
for(let i=0;i<5;i++){
 const y=171+i*96;
 const name=i<3?labels[i]:add();const body=i<3?bodies[i]:add();
 style(name,rows[i][0],64,y+10,245,62,28,true,'#155EEF');
 style(body,rows[i][1],340,y+8,876,72,24,false,'#101828');
 const line=i<3?rules[i]:s.shapes.add({geometry:'rect',fill:'#DCE4F2',line:{fill:'none',width:0}});
 line.position={left:64,top:y-5,width:1152,height:1};
}
s.speakerNotes.text=`3팀 소개와 역할 분담\n권장 시간: 0:45\n\n발표 대본\n저희는 3팀이며 다섯 명이 함께 작업했습니다. 팀장 양성훈 님은 산출물 문서 작업과 작업물 관리, 수정을 맡았습니다. 김지훈 A 님은 국내외 기사 요약과 번역을 담당했습니다. 홍록기 님은 회원가입과 로그인, Supabase 데이터베이스 연동, 구글 소셜 로그인과 보안 처리를 구현했습니다. 저는 조정한으로, 알림과 카테고리 지정 등 설정 기능과 메인화면 연동을 맡았고 오늘 발표를 진행하고 있습니다. 박수민 님은 기획과 로그인·비로그인 메인화면, 설정화면 UI를 담당했습니다. 각자의 작업을 사용자가 끝까지 이용할 수 있는 흐름으로 연결하는 것이 공동 과제였습니다.\n\n자료 근거\n2026-11-13 사용자 제공 팀 구성과 담당 역할. 알림 지정은 담당 업무 설명이며 외부 알림 발송의 운영 완료를 의미하지 않음.`;
// Keep the existing cover design and add the confirmed team identity.
const cover=p.slides.items[0];
const footer=cover.shapes.items.find(x=>Math.abs(x.position.top-650)<1);
if(footer) footer.text='3팀  /  프로젝트 피치  /  2026.11';
const coverNotes=cover.speakerNotes.text;
cover.speakerNotes.text=coverNotes.replace('안녕하세요.','안녕하세요. 3팀 발표를 맡은 조정한입니다.');
await (await PresentationFile.exportPptx(p)).save(path.join(B,'candidate-team.pptx'));
for(let i=0;i<10;i++){
 const blob=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(B,`team-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
}
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:path.join(B,'candidate-team.pptx'),finalPath:path.join(ROOT,'output','DAIT_3팀_피치덱_10장.pptx'),explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],pythonExecutable:'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe',integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],fontPolicy:{basis:'design',families:['Malgun Gothic']},verifyArtifactToolImport:true,receiptPath:path.join(B,'validation-team.json')});
console.log(JSON.stringify({path:result.finalPath,slides:result.firstPartyImport.slideCount,findings:result.presentationLayout.findingCount}));
