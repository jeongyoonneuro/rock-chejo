import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import uuid
from streamlit_calendar import calendar
from datetime import datetime # 💡 날짜 계산을 위해 추가된 라이브러리

# 페이지 설정

st.set_page_config(page_title="락페 체조 위원회 일정 공유방", page_icon="🎸", layout="wide")

# 페이지 설정
st.set_page_config(page_title="락페 체조 위원회 일정 공유방", page_icon="🎸", layout="wide")

# 💡 구글 Noto Sans KR 폰트 적용 CSS 주입
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
        
        html, body, [class*="css"], [class*="st-"] {
            font-family: 'Noto Sans KR', sans-serif !important;
        }
        
        /* 📅 달력 내부 텍스트 줄바꿈 강제 (말줄임표 절대 방지) */
        .fc-event-main, .fc-event-title, .fc-event-title-container, .fc-daygrid-event {
            white-space: normal !important;
            overflow: visible !important;
            word-wrap: break-word !important;
            word-break: keep-all !important;
            height: auto !important;
            padding: 2px !important;
        }
    </style>
""", unsafe_allow_html=True)

# 💡 화면 중앙에 떠오르는 팝업창 함수
@st.dialog("🎵 일정 상세 정보")
def show_event_popup(festival, full_date, members, memo):
    st.markdown(f"### {festival}")
    st.caption(f"📅 선택한 날짜: {full_date}")
    st.success(f"**🤸 참여 멤버:** {members}")
    if memo:
        st.info(f"**💬 멤버들의 메모:** {memo}")

st.title("🎸 락페 체조 위원회 일정 공유방")
st.subheader("함께 체조할 사람들 여기 모여라")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_NAME = "Sheet1" 

# 세션 상태 초기화 (폼 초기화용)
if "form_key" not in st.session_state:
    st.session_state.form_key = 0
if "success_msg" not in st.session_state:
    st.session_state.success_msg = ""

# 💡 날짜 문자열(YYYY-MM-DD)을 받아 요일을 추가해주는 헬퍼 함수
def add_weekday(date_str):
    date_str = date_str.strip()
    if "(" in date_str: # 이미 요일이 괄호로 붙어있으면 그대로 반환
        return date_str
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        return f"{date_str} ({weekdays[dt.weekday()]})"
    except ValueError:
        return date_str # 형식이 안 맞으면 원본 반환

# 1) 락페스티벌 프리셋 데이터 불러오기
@st.cache_data(ttl=600) 
def load_festivals():
    try:
        fest_df = conn.read(worksheet="Festivals", ttl=600).dropna(how="all")
        fest_dict = {}
        for _, row in fest_df.iterrows():
            fest_name = str(row['Festival']).strip()
            # 시트에서 읽어온 날짜에 일괄적으로 요일 붙이기
            dates = [add_weekday(d) for d in str(row['Available_Dates']).split(',')]
            fest_dict[fest_name] = dates
        return fest_dict
    except Exception as e:
        st.error(f"⚠️ 'Festivals' 시트를 읽는 중 오류 발생: {e}")
        return {}

# 2) 유저 일정 데이터 불러오기
@st.cache_data(ttl=30) 
def load_user_data():
    try:
        return conn.read(worksheet=SHEET_NAME, ttl=30).dropna(how="all")
    except Exception as e:
        st.sidebar.warning(f"시트 읽기 실패: {e}")
        return pd.DataFrame(columns=['ID', 'Name', 'Password', 'Festival', 'Dates', 'Memo'])

fest_dict = load_festivals()
df = load_user_data()

# 탭 구성
tab1, tab2, tab3 = st.tabs(["👥 겹치는 일정 확인", "➕ 내 일정 등록", "⚙️ 일정 수정/삭제"])

# ==========================================
# TAB 1: 겹치는 일정 확인
# ==========================================
with tab1:

    if df.empty or len(df) == 0:
        st.info("아직 등록된 일정이 없습니다. 두 번째 탭에서 첫 일정을 등록해보세요!")
    else:
        df_display = df.copy()
        df_display['Date_List'] = df_display['Dates'].astype(str).str.split(',')
        df_exploded = df_display.explode('Date_List')
        
        # 💡 예전에 등록한 데이터(요일이 없는 데이터)에도 요일 강제 추가하여 통일감 부여
        df_exploded['Date_List'] = df_exploded['Date_List'].apply(add_weekday)
        
        all_festivals = sorted(df['Festival'].unique().tolist())
        
        #view_mode = st.radio("👀 보기 방식 선택", ["📅 전체 일정 한눈에 보기", "💬 락페별 상세 멤버·메모 보기"], horizontal=True)
        #st.divider()
        view_mode = st.radio(
            "보기 방식 선택", # 접근성을 위해 텍스트는 남겨두지만 화면에선 완전히 숨겨집니다.
            ["📅 전체 일정 한눈에 보기", "💬 락페별 상세 멤버·메모 보기"], 
            horizontal=True,
            label_visibility="collapsed" # 💡 라벨과 줄바꿈(여백)을 모두 없애는 핵심 옵션!
        )
        
        if view_mode == "💬 락페별 상세 멤버·메모 보기":
            # 1. 마크다운을 이용해 원하는 크기의 제목을 먼저 출력합니다. (### 는 큰 글씨, #### 는 중간 글씨)
            st.markdown("##### 🎯 락페스티벌별로 보기")

            # 2. 실제 셀렉트박스의 기본 라벨은 숨겨버립니다.
            selected_fest = st.selectbox(
                "락페스티벌별로 보기", 
                ["전체보기"] + all_festivals, 
                label_visibility="collapsed"
            )
            filtered_df = df_exploded if selected_fest == "전체보기" else df_exploded[df_exploded['Festival'] == selected_fest]
            
            if filtered_df.empty:
                st.write("해당하는 일정이 없습니다.")
            else:
                match_df = filtered_df.groupby(['Festival', 'Date_List']).agg({
                    'Name': lambda x: ", ".join(sorted(list(set(x)))),
                    'Memo': lambda x: " | ".join([str(m) for m in x if pd.notna(m) and str(m).strip() != ""]),
                    'ID': 'count'
                }).reset_index()
                
                match_df.columns = ['락페스티벌', '날짜', '참여하는 사람들', '한줄 메모 모음', '인원수']
                match_df = match_df.sort_values(by=['날짜', '인원수'], ascending=[True, False])
                
                for idx, row in match_df.iterrows():
                    with st.container(border=True):
                        if row['인원수'] >= 2:
                            st.success(f"🔥 **[{row['락페스티벌']}] {row['날짜']}** — 총 {row['인원수']}명 겹침!")
                        else:
                            st.info(f"📌 **[{row['락페스티벌']}] {row['날짜']}** — 현재 {row['인원수']}명 참여")
                        st.caption(f"🤸 **멤버:** {row['참여하는 사람들']}")
                        if row['한줄 메모 모음']:
                            st.write(f"💬 *{row['한줄 메모 모음']}*")
        
        else:
            st.markdown("#### 📅 락페스티벌 Monthly 캘린더")
            st.caption("👆 달력 안의 일정을 클릭하면 아래에 상세 멤버와 메모가 표시됩니다!")
            
            color_palette = ["#FF6C6C", "#4782F6", "#56C173", "#F2A93B", "#9D65C9", "#E056FD", "#34E7E4"]
            fest_colors = {fest: color_palette[i % len(color_palette)] for i, fest in enumerate(all_festivals)}
            
            calendar_events = []
            
            # 💡 기존 그룹화 로직에 'Memo'도 함께 가져오도록 추가
            cal_df = df_exploded.groupby(['Date_List', 'Festival']).agg({
                'Name': lambda x: ", ".join(sorted(list(set(x)))),
                'Memo': lambda x: " | ".join([str(m) for m in x if pd.notna(m) and str(m).strip() != ""]),
                'ID': 'count'
            }).reset_index()

            for _, row in cal_df.iterrows():
                date_str = str(row['Date_List']).strip()
                pure_date = date_str[:10] 
                
                if len(pure_date) == 10: 
                    # 💡 수정된 부분: \n 을 사용해 멤버 이름을 다음 줄에 추가
                    event_title = f"[{row['Festival']}] {row['ID']}명\n└ 🤸 {row['Name']}"
                    
                    calendar_events.append({
                        "title": event_title,
                        "start": pure_date,
                        "color": fest_colors.get(row['Festival'], "#3788d8"),
                        "allDay": True,
                        "extendedProps": {
                            "festival": row['Festival'],
                            "members": row['Name'],
                            "memo": row['Memo'],
                            "full_date": date_str
                        }
                    })
            calendar_options = {
                "initialView": "dayGridMonth",
                "headerToolbar": {
                    "left": "prev,next today",
                    "center": "title",
                    "right": "dayGridMonth,listMonth"
                },
                "buttonText": {"today": "오늘", "dayGridMonth": "달력형", "listMonth": "목록형"},
                "height": 650,
                "displayEventTime": False,
            }
            
            # 💡 달력 iframe 안으로 직접 뚫고 들어가는 전용 CSS
            calendar_css = """
                /* 공통: 줄바꿈 문자를 인식하도록 pre-wrap 설정 */
                .fc-event-title, .fc-event-main {
                    white-space: pre-wrap !important; 
                    word-wrap: break-word !important;
                    word-break: keep-all !important;
                }
                .fc-h-event {
                    height: auto !important;
                    padding-bottom: 2px !important;
                }
                
                /* 👇 1. 달력형(Grid) 설정: 최대 2줄까지만 허용하고 나머지는 숨김 처리 */
                .fc-daygrid-event .fc-event-title {
                    display: -webkit-box !important;
                    -webkit-line-clamp: 2 !important; 
                    -webkit-box-orient: vertical !important;
                    overflow: hidden !important;
                }
                
                /* 👇 2. 목록형(List) 설정: 텍스트 제한 없이 모든 줄을 표시하고 all-day 열은 삭제 */
                .fc-list-event-title {
                    display: block !important;
                    white-space: pre-wrap !important;
                }
                .fc-list-event-time {
                    display: none !important;
                }
            """
            
            if calendar_events:
                # 💡 여기에 custom_css=calendar_css 파라미터를 추가합니다!
                cal_state = calendar(
                    events=calendar_events, 
                    options=calendar_options, 
                    custom_css=calendar_css, 
                    key="monthly_cal"
                )
                
                if cal_state and "eventClick" in cal_state:
                    event_data = cal_state["eventClick"]["event"]
                    props = event_data.get("extendedProps", {})
                    
                    # 위에서 만든 팝업 함수 호출
                    show_event_popup(
                        props.get('festival', ''),
                        props.get('full_date', ''),
                        props.get('members', ''),
                        props.get('memo', '')
                    )
            else:
                st.warning("달력에 표시할 유효한 날짜 데이터가 없습니다.")

# ==========================================
# TAB 2: 내 일정 일괄 등록
# ==========================================
with tab2:
    # 1. 마크다운을 이용해 원하는 크기의 제목을 먼저 출력합니다. (### 는 큰 글씨, #### 는 중간 글씨)
    st.markdown("### ➕ 한 번에 여러 락페 일정 등록하기")

    if st.session_state.success_msg:
        st.success(st.session_state.success_msg)
        st.session_state.success_msg = ""
    
    if not fest_dict:
        st.warning("구글 시트의 'Festivals' 탭을 먼저 확인해주세요.")
    else:
        fk = st.session_state.form_key 
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("👤 이름 (닉네임)", max_chars=10, key=f"name_{fk}")
        with col2:
            password = st.text_input("🔒 비밀번호 (4자리)", type="password", max_chars=4, key=f"pw_{fk}")
        
        st.divider()
        
        selected_festivals = st.multiselect(
            "🎸 1. 참여 예정인 락페스티벌을 모두 골라주세요", 
            list(fest_dict.keys()), 
            key=f"fests_{fk}"
        )
        
        user_inputs = {}
        if selected_festivals:
            st.markdown("#### 📅 2. 선택한 락페스티벌의 날짜를 골라주세요")
            for fest in selected_festivals:
                with st.container(border=True):
                    st.markdown(f"**🎵 {fest}**")
                    dates = st.multiselect(f"[{fest}] 참여 날짜 선택", fest_dict[fest], key=f"dates_{fest}_{fk}")
                    memo = st.text_input(f"[{fest}] 메모 (선택)", placeholder="예: 토요일 슬램존 대기", key=f"memo_{fest}_{fk}")
                    user_inputs[fest] = {"dates": dates, "memo": memo}
            
            st.divider()
            submit_btn = st.button("💾 3. 위 일정 구글 시트에 최종 등록하기", type="primary", use_container_width=True)
            
            if submit_btn:
                if not name or not password:
                    st.error("이름과 비밀번호를 위쪽에 입력해주세요!")
                else:
                    is_valid = True
                    for fest in selected_festivals:
                        if not user_inputs[fest]["dates"]:
                            st.error(f"⚠️ '{fest}'의 참여 날짜를 최소 하루 이상 선택해주세요!")
                            is_valid = False
                            break
                    
                    if is_valid:
                        new_rows = []
                        for fest in selected_festivals:
                            dates_str = ", ".join(user_inputs[fest]["dates"])
                            new_rows.append({
                                "ID": str(uuid.uuid4())[:8],
                                "Name": name,
                                "Password": password,
                                "Festival": fest,
                                "Dates": dates_str,
                                "Memo": user_inputs[fest]["memo"]
                            })
                        
                        new_df = pd.DataFrame(new_rows)
                        updated_df = pd.concat([df, new_df], ignore_index=True)
                        
                        try:
                            conn.update(worksheet=SHEET_NAME, data=updated_df)
                            st.cache_data.clear()
                            
                            st.session_state.success_msg = f"🎉 {name}님의 일정이 성공적으로 등록되었습니다! 첫 번째 탭에서 확인해보세요."
                            st.session_state.form_key += 1 
                            st.rerun()
                            
                        except Exception as write_error:
                            st.error(f"❌ 구글 시트에 저장하는 중 에러가 발생했습니다: {write_error}")

# ==========================================
# TAB 3: 일정 수정/삭제
# ==========================================
with tab3:
    # 1. 마크다운을 이용해 원하는 크기의 제목을 먼저 출력합니다. (### 는 큰 글씨, #### 는 중간 글씨)
    st.markdown("### ⚙️ 내 일정 관리")

    
    if df.empty or len(df) == 0:
        st.write("등록된 일정이 없습니다.")
    else:
        search_name = st.text_input("수정/삭제할 본인의 이름(닉네임) 입력")
        input_pw = st.text_input("비밀번호 입력", type="password")
        
        if search_name and input_pw:
            match_name = df['Name'].astype(str).str.strip() == search_name.strip()
            match_pw = df['Password'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == input_pw.strip()
            
            user_records = df[match_name & match_pw]
            
            if user_records.empty:
                st.error("이름 또는 비밀번호가 일치하는 일정이 없습니다. (오타나 띄어쓰기를 확인해주세요!)")
            else:
                st.success(f"🔑 {search_name}님의 일정을 찾았습니다. 관리할 락페스티벌을 선택하세요.")
                
                edit_target = st.selectbox("수정/삭제할 락페스티벌", user_records['Festival'].tolist())
                
                selected_record = user_records[user_records['Festival'] == edit_target].iloc[0]
                record_id = selected_record['ID']
                
                current_dates = [d.strip() for d in str(selected_record['Dates']).split(',')]
                # 수정 모드에서도 옵션에 요일이 제대로 보이도록 처리
                available_dates = fest_dict.get(edit_target, [add_weekday(d) for d in current_dates]) 
                
                edit_dates = st.multiselect("날짜 수정", available_dates, default=[add_weekday(d) for d in current_dates if add_weekday(d) in available_dates])
                edit_memo = st.text_input("메모 수정", value=str(selected_record['Memo']) if pd.notna(selected_record['Memo']) else "")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ 수정 내용 저장하기"):
                        if not edit_dates:
                            st.error("날짜를 최소 하나 이상 선택해주세요.")
                        else:
                            df.loc[df['ID'] == record_id, 'Dates'] = ", ".join(edit_dates)
                            df.loc[df['ID'] == record_id, 'Memo'] = edit_memo
                            try:
                                conn.update(worksheet=SHEET_NAME, data=df)
                                st.cache_data.clear()
                                st.success("일정이 성공적으로 수정되었습니다!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"수정 중 오류 발생: {e}")
                            
                with col2:
                    if st.button("❌ 이 일정 삭제하기", type="primary"):
                        df_deleted = df[df['ID'] != record_id]
                        try:
                            conn.update(worksheet=SHEET_NAME, data=df_deleted)
                            st.cache_data.clear()
                            st.success(f"[{edit_target}] 일정이 삭제되었습니다.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"삭제 중 오류 발생: {e}")
