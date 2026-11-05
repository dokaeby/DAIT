"""FastAPI 응답을 화면에 표시하는 Streamlit 앱. 모델은 로드하지 않는다."""
import os
from urllib.parse import urlparse

import requests
import streamlit as st
from dotenv import load_dotenv


def read_backend_url():
    """백엔드(FastAPI) 서버 주소를 환경변수 BACKEND_URL에서 읽고 검증한다.

    입력: 없음(환경변수 BACKEND_URL과 .env 파일)
    출력: 검증된 백엔드 URL 문자열 (https://host:port 형태, 끝 "/" 제거됨)
    기능: BACKEND_URL이 비어 있거나 http/https 주소가 아니면 ValueError를 발생시킴.
    """
    load_dotenv(override=False, interpolate=False)  # 프로세스 환경변수 우선, 문자열 치환 안 함.
    value = os.getenv("BACKEND_URL")
    if value is None or not value.strip():
        raise ValueError("BACKEND_URL 설정이 필요합니다.")
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("BACKEND_URL에는 http:// 또는 https:// 주소를 설정하세요.")
    return value


def request_answer(backend_url, prompt):
    """백엔드 /chat 엔드포인트에 질문을 POST로 보내 완성된 답변을 받아온다.

    입력: backend_url (검증된 백엔드 주소), prompt (사용자 질문 문자열)
    출력: 답변 문자열 (백엔드 JSON 응답의 "answer" 필드)
    기능: HTTP 4xx/5xx나 answer가 비어 있으면 예외를 발생시킴 (timeout: 연결 5초/읽기 180초).
    """
    with requests.post(
        f"{backend_url}/chat",  # Streamlit 서버가 FastAPI를 HTTP로 호출한다.
        json={"prompt": prompt},  # Python 딕셔너리를 JSON 요청 본문으로 보낸다.
        timeout=(5, 180),  # 연결 5초, 응답 읽기 대기 180초. 총 실행 시간 제한과 다르다.
    ) as response:
        response.raise_for_status()  # HTTP 4xx/5xx는 답변으로 취급하지 않는다.
        data = response.json()  # 완성된 JSON 응답을 Python 값으로 변환한다.
    if not isinstance(data, dict) or not isinstance(data.get("answer"), str) or not data["answer"].strip():
        raise ValueError("answer 문자열이 없는 응답입니다.")
    return data["answer"]



def main():
    """Streamlit 앱의 화면(유저 인터페이스)을 렌더링하고 대화 흐름을 처리한다.

    입력: 없음(st.chat_input으로 사용자 질문을 실시간 받음)
    출력: 없음(화면에 사용자 질문과 백엔드 답변, 오류 메시지를 표시함)
    기능: URL 검증→질문 입력(1~500자)→백엔드 호출→결과/오류를 화면에 표시.
    """
    st.title("백엔드가 답하는 학습 도우미")
    st.caption("FastAPI · 로컬 CPU · 완성된 답변")
    try:
        backend_url = read_backend_url()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()  # FastAPI와는 별개로 이 화면의 실행만 중단한다.

    prompt = st.chat_input("짧은 질문을 입력하세요")
    if prompt is None:
        return
    prompt = prompt.strip()
    if not prompt or len(prompt) > 500:
        st.warning("공백을 제외한 1~500자의 질문을 입력하세요.")
        return

    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        try:
            with st.spinner("백엔드가 답변을 생성하고 있습니다..."):
                answer = request_answer(backend_url, prompt)
            st.write(answer)
        except requests.HTTPError as exc:
            st.error(f"백엔드 요청 실패: HTTP {exc.response.status_code}. 실행 버전과 입력을 확인하세요.")
        except requests.RequestException:
            st.error("백엔드 연결이 끊겼거나 응답을 기다리다 실패했습니다. 서버 상태를 확인하세요.")
        except (ValueError, RuntimeError):
            st.error("답변 생성이 완료되지 않았습니다. 현재 표시된 내용은 완성된 답변이 아닙니다.")



if __name__ == "__main__":
    main()