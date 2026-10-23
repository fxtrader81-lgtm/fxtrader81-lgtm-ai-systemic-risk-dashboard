"""Reusable owner gate for commercially sensitive dashboard downloads."""
from __future__ import annotations

import time
from urllib.parse import quote
from uuid import uuid4

import streamlit as st

from core.download_access import (
    contact_email,
    credentials_configured,
    interest_stats,
    record_interest,
    verify_owner_credentials,
)


OWNER_SESSION_KEY = "download_owner_authenticated"
VISITOR_SESSION_KEY = "download_interest_session"
LOGIN_FAILURE_KEY = "download_owner_login_failures"
LOGIN_LOCK_KEY = "download_owner_login_lock_until"
LOGIN_MAX_FAILURES = 5
LOGIN_LOCK_SECONDS = 300


def owner_authenticated() -> bool:
    return bool(st.session_state.get(OWNER_SESSION_KEY, False))


def _visitor_token() -> str:
    if VISITOR_SESSION_KEY not in st.session_state:
        st.session_state[VISITOR_SESSION_KEY] = uuid4().hex
    return st.session_state[VISITOR_SESSION_KEY]


def _contact_request(resource_label: str) -> None:
    email = contact_email()
    st.info(f"验证未通过。如需索取「{resource_label}」，请联系 {email}。")
    subject = quote(f"申请索取看板资料：{resource_label}")
    st.link_button("发送邮件索取", f"mailto:{email}?subject={subject}", use_container_width=True)
    st.caption("失败验证仅记录资料名称、时间和匿名会话标识；不收集IP、姓名或邮箱。")


def _owner_stats_caption() -> None:
    stats = interest_stats()
    st.caption(
        f"外部失败验证：{stats['total_clicks']}次 · "
        f"匿名会话近似{stats['approx_sessions']}个 · "
        f"最后记录：{stats['last_clicked_at'] or '尚无'}"
    )


@st.dialog("下载资料验证")
def _download_login_dialog(
    label: str,
    data,
    *,
    file_name: str,
    mime: str,
    key: str,
    use_container_width: bool,
) -> None:
    if not credentials_configured():
        record_interest(file_name, _visitor_token())
        st.warning("服务器尚未配置下载口令。")
        _contact_request(label)
        return
    remaining = int(max(0, st.session_state.get(LOGIN_LOCK_KEY, 0) - time.monotonic()))
    if remaining:
        st.warning(f"失败次数过多，请{remaining}秒后再试。")
        _contact_request(label)
        return
    with st.form(f"download_login_form_{key}"):
        username = st.text_input("用户名", value="", placeholder="请输入用户名")
        password = st.text_input("口令", type="password")
        submitted = st.form_submit_button("验证", use_container_width=True)
    if submitted:
        if verify_owner_credentials(username, password):
            st.session_state[OWNER_SESSION_KEY] = True
            st.session_state[LOGIN_FAILURE_KEY] = 0
            st.session_state[LOGIN_LOCK_KEY] = 0
            st.success("验证通过，本会话的下载权限已解锁。")
            _owner_stats_caption()
            st.download_button(
                f"下载 {label}",
                data,
                file_name=file_name,
                mime=mime,
                key=f"{key}_verified_dialog",
                use_container_width=True,
            )
        else:
            record_interest(file_name, _visitor_token())
            failures = int(st.session_state.get(LOGIN_FAILURE_KEY, 0)) + 1
            if failures >= LOGIN_MAX_FAILURES:
                st.session_state[LOGIN_FAILURE_KEY] = 0
                st.session_state[LOGIN_LOCK_KEY] = time.monotonic() + LOGIN_LOCK_SECONDS
                st.error("用户名或口令不正确。已暂停尝试5分钟。")
            else:
                st.session_state[LOGIN_FAILURE_KEY] = failures
                st.error(f"用户名或口令不正确，还可尝试{LOGIN_MAX_FAILURES - failures}次。")
            _contact_request(label)


def protected_download_button(
    label: str,
    data,
    *,
    file_name: str,
    mime: str,
    key: str,
    use_container_width: bool = False,
):
    """Render a download; unauthenticated clicks request credentials in-place."""
    if owner_authenticated():
        return st.download_button(
            label,
            data,
            file_name=file_name,
            mime=mime,
            key=key,
            use_container_width=use_container_width,
        )
    if st.button(label, key=f"request_{key}", use_container_width=use_container_width):
        _download_login_dialog(
            label,
            data,
            file_name=file_name,
            mime=mime,
            key=key,
            use_container_width=use_container_width,
        )
    return False
