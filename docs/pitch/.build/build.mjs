import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const MODULES='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules';
process.env.RUNTIME_NODE_MODULES=MODULES;
const require=createRequire(path.join(MODULES,'__runtime__.cjs'));
const {Presentation,PresentationFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const sharp=require('sharp');
const ROOT='C:/DAIT/docs/pitch';
const BUILD=path.join(ROOT,'.build');
const SRC='C:/Users/Playdata/Desktop/발표자료/첨부사진';
const SKILL='C:/Users/Playdata/.codex/plugins/cache/openai-primary-runtime/presentations/26.1112.11011/skills/presentations';
const W=1280,H=720,FONT='Malgun Gothic';
const C={blue:'#155EEF',ink:'#101828',muted:'#667085',light:'#F3F6FD',line:'#DCE4F2',white:'#FFFFFF',navy:'#102A56'};
const ppt=Presentation.create({slideSize:{width:W,height:H}});
const records=[];
function txt(s,text,x,y,w,h,size=26,color=C.ink,bold=false){
  const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  sh.text=text;
  sh.text.style={typeface:FONT,fontSize:size,color,bold,insets:0,autoFit:'none',wrap:'square',verticalAlignment:'top'};
  return sh;
}
function rule(s,x,y,w,color=C.line){s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:1},fill:color,line:{fill:'none',width:0}});}
function slide(title,n,dark=false){
  const s=ppt.slides.add();s.background.fill=dark?C.navy:C.white;
  txt(s,title,64,52,1152,104,44,dark?C.white:C.ink,true);
  txt(s,String(n).padStart(2,'0'),1160,674,56,24,17,dark?'#B5C8EA':C.muted);
  return s;
}
function notes(s,title,duration,script,source='',cue=''){
  const note=`${title}\n권장 시간: ${duration}\n\n${script}\n${cue?'\n화면 진행\n'+cue+'\n':''}${source?'\n자료 근거\n'+source:''}`;
  s.speakerNotes.text=note;records.push({title,duration,script,cue,source});
}
async function screenshot(s,file,box,region){
  const source=path.join(SRC,file);let pipe=sharp(source);
  if(region) pipe=pipe.extract({left:region[0],top:region[1],width:region[2],height:region[3]});
  const buffer=await pipe.png().toBuffer();
  return s.images.add({blob:new Uint8Array(buffer),contentType:'image/png',alt:file+' 실제 배포 화면 발췌',fit:'contain',position:{left:box[0],top:box[1],width:box[2],height:box[3]}});
}
function row(s,y,label,body){rule(s,64,y-18,1152);txt(s,label,64,y,280,55,31,C.blue,true);txt(s,body,374,y,820,76,26,C.ink);}

// 01
{
const s=ppt.slides.add();s.background.fill=C.navy;
txt(s,'DAIT',64,58,450,110,88,C.white,true);
txt(s,'국내외 뉴스를\n한곳에서 빠르게 이해하다',64,203,505,160,43,C.white,true);
txt(s,'관심사별 탐색과 한국어 요약,\n원문 확인을 연결하는 뉴스 큐레이션',64,405,470,105,25,'#CEDBF2');
await screenshot(s,'01_메인화면.png',[585,185,645,380],[78,128,1720,674]);
txt(s,'프로젝트 피치  /  2026.11',64,650,750,32,18,'#B5C8EA');
txt(s,'01',1160,674,56,24,17,'#B5C8EA');
notes(s,'DAIT 소개','0:30',`안녕하세요. 국내외 뉴스를 관심사에 맞게 탐색하고, 한국어 요약으로 핵심을 파악하는 서비스 다잇을 소개합니다. 저희는 매일 AI 동향을 확인하는 개발자와 기획자를 첫 사용자로 설정했습니다. 현재 배포 화면은 경제와 사회 분야까지 함께 다룹니다. 오늘은 사용자가 필요한 기사를 찾고, 요약을 읽은 뒤 원문을 확인하는 흐름과 이를 구현한 설계를 중심으로 설명하겠습니다.`, '사용자 제공 01_메인화면.png. 캡처 내 기사 수는 해당 시점의 화면 표시이며 서비스 성과 지표가 아님.');
}
// 02
{
const s=slide('뉴스를 찾은 뒤에도 해야 할 일이 많습니다',2);
const items=[['01','탐색','여러 사이트를 오가며\n관심 있는 기사 찾기'],['02','이해','긴 해외 기사에서\n핵심 내용 파악하기'],['03','확인','요약의 출처를 찾고\n원문 내용 확인하기']];
items.forEach((v,i)=>{const x=64+i*395;txt(s,v[0],x,210,260,68,52,C.blue,true);txt(s,v[1],x,303,300,65,38,C.ink,true);txt(s,v[2],x,397,350,110,27,C.muted);});
txt(s,'첫 사용자: 매일 AI 동향을 확인하는 개발자와 기획자',64,590,1130,50,26,C.blue,true);
notes(s,'사용자 문제','1:00',`개발자나 기획자가 오늘의 AI 동향을 확인하는 상황을 생각해 보겠습니다. 먼저 여러 사이트에서 관심 있는 기사를 찾습니다. 제목이 흥미로워도 긴 본문을 읽어야 필요한 정보인지 판단할 수 있습니다. 해외 기사라면 언어를 이해하는 과정도 추가됩니다. 다른 사람이 작성한 요약을 보더라도 중요한 수치와 표현이 정확한지 확인하려면 다시 원문을 찾아야 합니다. 저희는 이 과정을 탐색, 이해, 확인으로 정리했습니다. 세 과정 사이에서 반복하는 행동을 줄이고, 필요한 정보를 판단할 수 있는 화면 흐름을 만드는 것이 목표입니다.`, 'docs/DAIT_v1.0.4/01_기본기획서_v1.0.4.md의 기획 배경·사용자 문제. 탐색 시간 단축은 제품 목표이며 측정된 성과가 아님.');
}
// 03
{
const s=slide('관심 주제를 저장해 탐색 범위를 좁힙니다',3);
txt(s,'국내 관심 주제 예시',64,174,540,42,28,C.blue,true);
txt(s,'해외 관심 주제 예시',664,174,550,42,28,C.blue,true);
await screenshot(s,'02_국내카테고리.png',[64,270,550,200],[590,364,283,56]);
await screenshot(s,'03_해외카테고리.png',[664,270,550,200],[795,202,310,60]);
rule(s,64,565,1152);
txt(s,'주제를 선택하면 자동 저장되고, 메인의 관심사 칩에 반영됩니다',64,595,1140,45,27,C.ink,true);
notes(s,'해결 방식과 관심사 설정','1:00',`다잇에서는 사용자가 관심 주제를 직접 선택합니다. 왼쪽은 국내, 오른쪽은 해외 관심 주제 설정 화면입니다. AI 분야에서는 모델과 연구, AI 에이전트, 개발 도구처럼 실제로 찾는 주제 단위로 탐색할 수 있도록 구성했습니다. 선택하거나 해제한 항목은 화면 안내처럼 자동 저장되며 메인 화면의 관심사 칩에 반영됩니다. 현재 관심사 매칭은 정해진 키워드 규칙을 사용합니다. 따라서 사용자 행동을 학습하는 추천으로 설명하지 않고, 사용자가 선택한 주제로 탐색 범위를 좁히는 기능으로 소개합니다. 다음 화면에서 이 설정이 뉴스 목록에 어떻게 연결되는지 보겠습니다.`, '사용자 제공 02_국내카테고리.png, 03_해외카테고리.png. 관심사 매칭 방식: docs/DAIT_v1.0.4/01_기본기획서_v1.0.4.md.');
}
// 04
{
const s=slide('실제 사용 흐름: 관심사 설정부터 원문 확인까지',4);
txt(s,'1. 관심 주제 선택',64,177,410,45,28,C.blue,true);
await screenshot(s,'04_카테고리저장.png',[530,164,686,100],[590,245,616,62]);
txt(s,'2. 해외 기사와 한국어 요약 확인',64,305,1120,45,28,C.blue,true);
await screenshot(s,'06_해외 메인화면.png',[64,368,1152,220],[450,600,1145,215]);
txt(s,'3. 카드의 ‘원문 열기’로 출처 확인',64,615,1140,45,29,C.ink,true);
notes(s,'배포 화면 기반 시연','2:30',`먼저 관심사 설정을 보겠습니다. 파란 테두리와 체크 표시가 선택한 주제를 나타냅니다. 국내와 해외 관심사를 각각 선택할 수 있고, 이 설정은 메인 화면의 소주제 칩에 반영됩니다. [관심사 선택 화면을 약 20초간 짚어 설명합니다.] 이제 해외 뉴스 목록을 보겠습니다. 상단에는 저장한 관심 주제와 주제별 기사 수가 표시됩니다. 한 기사가 여러 주제에 포함될 수 있고, 전체에서는 중복을 제외한다는 안내도 함께 제공합니다. [메인 화면에서 관심사 칩과 해외 선택 상태를 차례로 가리킵니다.] 기사 카드에는 영어 제목, 매체명과 발행 시각, 한국어 세 줄 요약이 배치되어 있습니다. 영어 제목을 읽고 긴 원문 전체로 바로 이동하기 전에, 요약을 통해 읽을 기사를 판단할 수 있습니다. 여기서 보여드리는 것은 제공받은 배포 화면의 한국어 요약이며, 별도 본문 번역 상세 화면은 이번 캡처에 포함되어 있지 않습니다. [기사 제목과 요약 영역을 충분히 보여줍니다.] 더 자세한 내용이 필요하면 오른쪽의 원문 열기를 사용합니다. 실제 원문 화면은 뒤의 검증 슬라이드에서 함께 보겠습니다. 이처럼 관심사 선택, 해외 기사 탐색, 한국어 요약, 출처 확인을 하나의 사용 흐름으로 연결했습니다.`, '사용자 제공 04_카테고리저장.png, 06_해외 메인화면.png. 수치와 기사 내용은 캡처 시점의 표시 예시. 기사에 등장하는 제품명·성능 수치는 DAIT의 성과가 아님.', '캡처만으로 발표하면 각 영역을 가리키며 설명합니다. 라이브 시연 시 동일한 흐름을 사용합니다. 브라우저 전환·화면 설명·호흡을 포함해 2분 30초로 배정합니다.');
}
// 05
{
const s=slide('뉴스 처리와 사용자 조회를 분리한 구조',5);
txt(s,'뉴스 처리',64,175,300,42,28,C.blue,true);
const stages=[['수집','RSS·본문 추출'],['AI 처리','번역·요약·검증'],['저장','기사·처리 결과']];
stages.forEach((a,i)=>{const x=64+i*395;txt(s,a[0],x,245,350,60,38,C.ink,true);txt(s,a[1],x,318,355,50,26,C.muted);if(i<2)txt(s,'→',x+331,245,60,60,38,C.blue);});
rule(s,64,417,1152);
txt(s,'사용자 조회',64,456,300,42,28,C.blue,true);
txt(s,'화면 요청',64,526,270,58,35,C.ink,true);txt(s,'→',365,526,55,60,38,C.blue);
txt(s,'API·캐시·DB',458,526,390,58,35,C.ink,true);txt(s,'→',895,526,55,60,38,C.blue);txt(s,'저장 결과 제공',980,526,270,58,31,C.ink,true);
notes(s,'전체 구조','1:30',`방금 보신 기사는 사용자가 화면을 열 때 준비하는 것이 아니라, 처리 경로에서 수집하고 AI로 가공한 뒤 저장하는 방식으로 설계했습니다. 뉴스 처리 경로에서는 RSS와 기사 본문을 수집하고, 필요한 번역과 요약을 수행합니다. 이후 결과를 검증하고 저장합니다. 사용자 조회 경로에서는 화면이 API에 요청하면 캐시와 데이터베이스에서 저장 결과를 읽어 전달합니다. 이 구분은 같은 기사를 여러 사용자가 읽을 때 매번 수집과 AI 호출을 반복하지 않도록 하기 위한 선택입니다. 처리 결과를 공유하고, 외부 수집이나 AI 처리의 문제와 사용자 조회의 문제를 나누어 추적할 수 있습니다. 구현은 FastAPI 기반 API, 데이터베이스, Redis와 별도 뉴스 처리 파이프라인으로 구성했습니다. 이 그림은 세부 배포 인스턴스를 생략하고 처리와 조회의 책임을 보여주는 구조도입니다.`, 'docs/DAIT_v1.0.4/01_기본기획서_v1.0.4.md 제품 원칙, 02_시스템상세설계서_v1.0.4.md. 최종 배포 환경별 설정과 연결 상태는 별도 검증 대상.');
}
// 06
{
const s=slide('반복 처리와 실패를 다루는 설계',6);
row(s,199,'중복 방지','기사 식별 기준으로 중복 저장·처리를 제어');
row(s,345,'결과 재사용','저장된 처리 결과와 캐시를 활용');
row(s,491,'실패 구분','본문 부족·처리 실패를 정상 결과와 구분');
notes(s,'핵심 기술 판단','1:30',`핵심 설계 선택은 세 가지입니다. 먼저 중복 방지입니다. 뉴스 수집을 반복하면 같은 기사가 다시 들어올 수 있습니다. 그래서 기사 식별 기준을 두고 중복 저장과 후속 처리를 제어하도록 설계했습니다. 다음은 결과 재사용입니다. 이미 처리한 기사는 저장 결과와 캐시를 활용합니다. 여러 사용자가 같은 기사를 조회해도 준비된 결과를 공유할 수 있습니다. 여기서 비용이나 응답 시간이 얼마나 개선됐는지는 별도 측정이 필요하므로 개선율을 주장하지 않습니다. 마지막은 실패 구분입니다. 본문이 충분하지 않거나 AI 처리가 실패한 결과를 정상 기사처럼 다루지 않도록 상태를 구분합니다. 정상 경로가 연결되는 것과 함께, 어디에서 실패했는지 설명할 수 있어야 한다는 점을 기준으로 삼았습니다.`, 'docs/DAIT_v1.0.4/01_기본기획서_v1.0.4.md의 공용 처리·결과 재사용·실패 가시성 원칙. 성능 및 비용 개선율은 미측정.');
}
// 07
{
const s=slide('문제 해결 사례: 제목 번역의 문맥 부족',7);
txt(s,'개발 기록 사례',64,175,800,35,22,C.muted);
txt(s,'midterms',64,244,1100,92,64,C.blue,true);
txt(s,'문제',64,374,200,45,28,C.muted,true);txt(s,'선거 기사를 ‘중간고사’로 해석',310,374,890,65,34,C.ink,true);
rule(s,64,459,1152);
txt(s,'개선',64,495,200,45,28,C.blue,true);txt(s,'정제한 본문 문맥을 제목 번역에 활용',310,495,890,65,32,C.ink,true);
txt(s,'정치·학업 문맥 구분과 실패 시 대체 경로를 검증',64,604,1140,45,25,C.muted);
notes(s,'기술적 문제 해결','1:00',`개발 기록에는 짧은 제목의 다의어를 잘못 해석한 사례가 있습니다. 선거 기사에 등장한 midterms를 중간고사로 번역해, 본문 요약과 제목의 의미가 어긋났습니다. 제목만으로는 의미를 판단할 문맥이 부족한 것이 원인이었습니다. 해결 과정에서는 정제한 본문 일부를 제목 번역의 문맥으로 활용하고, 반환 결과에서 제목만 추출하도록 개선했습니다. 정치 문맥과 학업 문맥이 구분되는지, 문맥 처리에 실패하면 제목 단독 번역 등 대체 경로로 이어지는지 검증했습니다. 이 사례는 개발 인수인계 기록을 바탕으로 정리한 것입니다. 오늘 제공된 화면에서 수정 전후를 직접 비교한 결과와는 구분합니다.`, 'C:/DAIT/HANDOVER.md 6~10절의 제목 문맥 번역·검증 기록. 수정 전후 화면을 재구성하거나 현재 배포 버전의 추가 검증을 수행하지 않음.');
}
// 08
{
const s=slide('검증 범위와 남은 품질 과제',8);
txt(s,'관심사 선택과 주제별 집계',64,175,530,42,27,C.blue,true);
await screenshot(s,'05_국내 메인화면.png',[64,235,548,170],[370,360,435,128]);
txt(s,'화면 확인: 관심사·국내외 목록·요약\n품질 검증: 사실 보존·문장 정보 밀도',64,435,550,95,25,C.ink);
txt(s,'원문 비교에 사용할 근거',664,175,550,42,27,C.blue,true);
await screenshot(s,'07_해외기사원문.png',[664,239,550,180],[330,132,840,160]);
txt(s,'핵심 주장·수치·고유명사를 대조',664,445,550,80,25,C.ink);
rule(s,64,568,1152);
txt(s,'추가 검증: 수치·고유명사 보존, 문장 품질, 실패·복구와 응답 시간',64,596,1152,65,25,C.ink,true);
notes(s,'검증 결과와 한계','1:00',`제공된 배포 화면에서는 관심사 선택 상태와 주제별 기사 수, 국내외 뉴스 목록, 한국어 요약과 원문 열기 진입점을 확인할 수 있습니다. 오른쪽은 해외 기사 원문 캡처입니다. 기사 요약과 원문을 비교할 때는 수치와 고유명사, 핵심 주장이 유지되는지를 확인해야 합니다. 다만 화면이 있다는 사실만으로 요약 정확도나 전체 사용 흐름의 성공률이 검증되는 것은 아닙니다. 국내 기사 캡처에는 기자 표기나 원문 확인 안내가 요약 줄에 포함된 사례도 보여, 요약의 정보 밀도를 개선할 필요가 있습니다. 자동 테스트 수는 문서별 기준이 달라 이번 덱에서는 확정 수치를 제시하지 않았습니다. 최종 발표 버전에서 수동 검증과 자동 검사 범위를 맞추고, 실패 복구와 응답 시간까지 확인하는 것이 다음 검증 과제입니다.`, '사용자 제공 05_국내 메인화면.png, 07_해외기사원문.png. 해외 원문은 06_해외 메인화면.png의 기사 흐름을 설명하는 사용자 제공 자료. 원문 기사 내용 자체의 사실 여부·최신성은 이번 제작에서 외부 검증하지 않음.');
}
// 09
{
const s=slide('팀 협업: 기능을 하나의 사용 흐름으로 통합',9);
row(s,199,'역할 연결','수집·AI 처리·API·화면·배포의 연결 지점 정의');
row(s,345,'계약과 상태 기준','요청·응답 형식과 처리 상태의 의미 공유');
row(s,491,'통합 검증','탐색·요약·원문 확인 흐름으로 연결 상태 점검');
notes(s,'팀 협업과 기여','0:45',`프로젝트는 수집과 AI 처리, API와 데이터, 화면과 배포가 하나의 사용 흐름으로 연결되어야 합니다. 협업에서 중요한 기준은 각 역할의 연결 지점입니다. API 요청과 응답 형식, 처리 상태의 의미가 일치해야 화면에서 결과를 올바르게 보여줄 수 있습니다. 또한 기능별 완료와 별도로 관심사 설정부터 기사 조회, 요약과 원문 확인까지 통합 경로를 점검해야 합니다. 이 슬라이드는 개인별 기여도가 아니라 역할 간 협업 기준을 정리한 것입니다. 팀원별 담당 결과물은 팀이 확정한 역할표에 따라 설명하겠습니다.`, '프로젝트 API·상태 계약 및 통합 검증 문서에 근거한 협업 구조. 개인 이름·담당·기여 비율은 제공되지 않아 기재하지 않음.');
}
// 10
{
const s=slide('현재 성과와 다음 검증 과제',10,true);
txt(s,'현재',64,206,200,50,29,'#B5C8EA',true);
txt(s,'관심사 탐색과 한국어 요약,\n원문 확인을 연결한 배포 화면',310,202,880,115,38,C.white,true);
rule(s,64,371,1152,'#49658F');
txt(s,'다음',64,416,200,50,29,'#B5C8EA',true);
txt(s,'실사용자의 탐색 시간·사용성 측정\n요약 품질과 운영 안정성 검증',310,416,880,113,32,C.white);
txt(s,'필요한 뉴스를 찾고, 이해하고, 확인하는 DAIT',64,609,1152,50,30,C.white,true);
notes(s,'마무리','0:45',`다잇은 관심사를 설정하고 국내외 기사를 탐색한 뒤, 한국어 요약과 원문을 확인하는 경험을 배포 화면으로 구현했습니다. 동시에 저장 결과의 재사용과 중복 방지, 실패 처리를 고려했습니다. 다음 단계에서는 실제 사용자가 필요한 정보를 찾는 데 걸리는 시간과 사용성을 측정하겠습니다. 요약의 정보 밀도와 사실 보존을 개선하고, 최종 배포 버전에서 오류 복구와 운영 안정성도 확인하겠습니다. 필요한 뉴스를 찾고, 이해하고, 확인하는 서비스 다잇이었습니다. 감사합니다.`, '사용자 제공 배포 캡처 및 프로젝트 기획·구현 문서. 시간 절감과 정확도 개선은 후속 측정 목표.');
}

records[3].script=`먼저 관심사 설정을 보겠습니다. 파란 테두리와 체크 표시가 선택한 주제를 나타냅니다. 화면에서는 모델과 연구, AI 에이전트, 개발 도구를 선택한 예시를 보여드리고 있습니다. 사용자는 국내와 해외 관심사를 각각 고를 수 있고, 선택한 항목은 메인 화면의 탐색 기준에 반영됩니다. [관심 주제의 선택 표시를 가리키며 설명합니다.] 이제 아래의 해외 기사 카드를 보겠습니다. 영어 원문 제목과 매체명, 발행 시각이 표시되고, 바로 오른쪽에 한국어 세 줄 요약을 제공합니다. 사용자는 긴 원문을 모두 읽기 전에 요약을 통해 필요한 기사인지 판단할 수 있습니다. [영어 제목과 한국어 요약 영역을 차례로 보여줍니다.] 요약을 읽을 때는 핵심 주장이 무엇인지, 주요 수치와 고유명사가 어떻게 표현되었는지도 확인할 수 있습니다. 다만 세 줄이라는 형식이 내용의 정확성을 보장하는 것은 아니므로, 필요한 경우 원문에서 확인하는 흐름을 함께 제공합니다. 오른쪽의 원문 열기가 그 연결 지점입니다. 원문을 열어 기사 전체의 맥락을 읽고 요약과 비교할 수 있습니다. [원문 버튼을 가리킵니다. 라이브 시연 시 원문을 열고 돌아옵니다.] 관심 주제 선택, 해외 기사 탐색, 한국어 요약, 원문 확인을 하나의 화면 흐름으로 연결한 것이 다잇의 핵심 경험입니다.`;
records[7].script=`화면과 정보 품질은 구분해서 검증했습니다. 왼쪽 화면에는 관심사별 기사 수와 국내외 구분이 표시됩니다. 이처럼 설정과 목록의 연결 상태를 확인하고, 기사 카드에서 한국어 요약과 원문 열기의 진입점을 확인했습니다. 오른쪽은 해외 기사의 원문입니다. 요약을 원문과 비교할 때는 수치와 고유명사, 핵심 주장이 유지되는지를 기준으로 삼습니다. 남은 과제도 있습니다. 국내 기사 예시에는 기자 표기나 원문 확인 안내가 요약에 포함된 사례가 있어, 요약의 정보 밀도를 개선할 필요가 있습니다. 최종 배포 버전을 기준으로 자동 검사와 수동 확인 범위를 맞추고, 실패 후 복구와 응답 시간까지 검증 범위를 넓히겠습니다.`;
records[8].script=`프로젝트에서는 수집과 AI 처리, API와 데이터, 화면과 배포가 하나의 사용 흐름으로 이어져야 합니다. 협업에서 중요한 기준은 각 역할의 연결 지점이었습니다. 요청과 응답 형식, 처리 상태의 의미를 공유해야 화면에서도 결과를 올바르게 표시할 수 있습니다. 또한 각 기능의 구현과 함께 관심사 설정부터 기사 조회, 요약과 원문 확인까지 통합 경로를 점검하는 기준을 세웠습니다. 팀의 결과물은 각 영역의 코드를 연결하고, 사용자가 끝까지 수행할 수 있는 흐름으로 맞추는 데 있습니다.`;
for(let i=0;i<records.length;i++){
 const r=records[i];ppt.slides.items[i].speakerNotes.text=`${r.title}\n권장 시간: ${r.duration}\n\n발표 대본\n${r.script}\n\n${r.cue?'화면 진행\n'+r.cue+'\n\n':''}자료 근거\n${r.source}`;
}
await fs.writeFile(path.join(BUILD,'notes.json'),JSON.stringify(records,null,2));
await fs.writeFile(path.join(BUILD,'presentation.json'),JSON.stringify(ppt.toProto()));
const candidate=path.join(BUILD,'candidate.pptx');
await (await PresentationFile.exportPptx(ppt)).save(candidate);
console.log(JSON.stringify({stage:'exported',candidate,slides:ppt.slides.items.length,notes:records.length}));
for(let i=0;i<ppt.slides.items.length;i++){
 const png=await ppt.export({slide:ppt.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(BUILD,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
 console.log(`Rendered ${i+1}`);
}
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const finalized=await finalizePresentation({
 workspaceDir:ROOT,candidatePath:candidate,finalPath:path.join(ROOT,'output','DAIT_피치덱_10장.pptx'),
 explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
 pythonExecutable:'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-611-0_26.1112.611.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe',
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
 fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,
 receiptPath:path.join(BUILD,'validation-final.json')
});
console.log(JSON.stringify(finalized));
