import json
import streamlit as st
import requests
import streamlit.components.v1 as components

# Read backend URL from Streamlit secrets if present, otherwise fall back to localhost
BACKEND_URL = "http://localhost:8000"
try:
    BACKEND_URL = st.secrets.get("BACKEND_URL", BACKEND_URL)
except Exception:
    BACKEND_URL = BACKEND_URL

st.set_page_config(layout="wide", page_title="Webpage Analyzer Platform", initial_sidebar_state="expanded")

if "page" not in st.session_state:
    st.session_state.page = "Analyze"
if "snapshot" not in st.session_state:
    st.session_state.snapshot = None
if "history" not in st.session_state:
    st.session_state.history = []
if "compare_result" not in st.session_state:
    st.session_state.compare_result = None
if "history_loaded" not in st.session_state:
    st.session_state.history_loaded = False

st.markdown(
    """
    <style>
      .reportview-container { background: #0f172a; color: #f8fafc; }
      .stApp { background: #0f172a; color: #f8fafc; }
      .stButton>button { background-color: #1f2937; color: #f8fafc; }
      .stTextInput>div>div>input { background-color: #111827; color: #f8fafc; border: 1px solid #374151; }
      .stSelectbox>div>div>div>select { background-color: #111827; color: #f8fafc; border: 1px solid #374151; }
      .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
      .stMarkdown p { color: #f8fafc; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("UI SPECIFICATION — WEBPAGE ANALYZER PLATFORM")
st.sidebar.markdown("---")
page_selection = st.sidebar.radio("Select page", ["Analyze", "Compare"], index=0 if st.session_state.page == "Analyze" else 1)
st.session_state.page = page_selection


def fetch_history(force=False):
    if st.session_state.history_loaded and not force:
        return st.session_state.history
    try:
        r = requests.get(f"{BACKEND_URL}/history", timeout=15)
        r.raise_for_status()
        st.session_state.history = r.json()
        st.session_state.history_loaded = True
    except Exception as e:
        st.error(f"Failed to load history: {e}")
        st.session_state.history = []
    return st.session_state.history


def load_snapshot(snapshot_id):
    try:
        r = requests.get(f"{BACKEND_URL}/snapshot/{snapshot_id}", timeout=15)
        r.raise_for_status()
        st.session_state.snapshot = r.json()
        st.success(f"Loaded snapshot {snapshot_id}")
    except Exception as e:
        st.error(f"Failed to load snapshot: {e}")
        st.session_state.snapshot = None


def analyze_url(url):
    try:
        r = requests.post(f"{BACKEND_URL}/analyze", json={"url": url}, timeout=45)
        r.raise_for_status()
        snapshot = r.json()
        st.session_state.snapshot = snapshot
        st.session_state.history_loaded = False
        fetch_history(force=True)
        st.success("Analysis complete")
    except Exception as e:
        st.error(f"Analyze failed: {e}")


def compare_snapshots(left_id, right_id):
    try:
        r = requests.post(f"{BACKEND_URL}/compare", json={"left_id": left_id, "right_id": right_id}, timeout=45)
        r.raise_for_status()
        st.session_state.compare_result = r.json()
    except Exception as e:
        st.error(f"Compare failed: {e}")
        st.session_state.compare_result = None


def render_dom_tree(tree):
    tree_json = json.dumps(tree)
    template = """
    <style>
      body { margin: 0; color: #f8fafc; background: #0f172a; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; }
      .tree-container { background: #111827; border: 1px solid #374151; border-radius: 12px; height: 540px; overflow: auto; padding: 16px; }
      .node { margin: 4px 0; cursor: pointer; }
      .node:hover { background: rgba(148, 163, 184, 0.12); }
      .children { margin-left: 18px; display: block; }
      .label { color: #e2e8f0; }
      .attrs { color: #94a3b8; font-size: 12px; margin-left: 8px; }
    </style>
    <div class="tree-container" id="tree"></div>
    <script>
      const tree = __TREE_JSON__;
      const root = document.getElementById('tree');
      function truncate(text) {
        if (!text) return '';
        return text.length > 120 ? text.slice(0, 120) + '…' : text;
      }
      function createNode(node) {
        const wrapper = document.createElement('div');
        const header = document.createElement('div');
        header.className = 'node';
        const label = document.createElement('span');
        label.className = 'label';
        label.textContent = node.name || '#text';
        header.appendChild(label);
        if (node.attrs) {
          const attrs = document.createElement('span');
          attrs.className = 'attrs';
          attrs.textContent = JSON.stringify(node.attrs);
          header.appendChild(attrs);
        }
        if (typeof node === 'string') {
          header.textContent = truncate(node);
        }
        wrapper.appendChild(header);
        const children = node.children || [];
        if (children.length) {
          const childWrapper = document.createElement('div');
          childWrapper.className = 'children';
          children.forEach(child => childWrapper.appendChild(createNode(child)));
          header.addEventListener('click', () => {
            childWrapper.style.display = childWrapper.style.display === 'none' ? 'block' : 'none';
          });
          wrapper.appendChild(childWrapper);
        }
        return wrapper;
      }
      if (tree) {
        root.appendChild(createNode(tree));
      }
    </script>
    """
    return template.replace("__TREE_JSON__", tree_json)


def render_analyze_html(snapshot):
    url = snapshot.get('url', '')
    tree = snapshot.get('tree', {})
    metrics = snapshot.get('summary', snapshot.get('metrics', {}))
    dom_html = render_dom_tree(tree)
    template = """
    <style>
      body { margin: 0; padding: 0; background: #0f172a; color: #f8fafc; font-family: Inter, sans-serif; }
      .split-pane { display: flex; width: 100%; min-height: 820px; }
      .pane { display: flex; flex-direction: column; background: #111827; border: 1px solid #1f2937; border-radius: 16px; overflow: hidden; }
      .left-pane { width: 40%; min-width: 320px; max-width: 55%; margin-right: 12px; }
      .right-pane { flex: 1; min-width: 420px; }
      .dragbar { width: 8px; cursor: col-resize; background: #1f2937; border-radius: 4px; margin: 0 4px; }
      .section-header { padding: 18px 20px; border-bottom: 1px solid #1f2937; font-size: 16px; font-weight: 700; color: #f8fafc; }
      .metrics-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; padding: 18px 20px; }
      .metric-card { background: #0f172a; border: 1px solid #1f2937; border-radius: 14px; padding: 16px; }
      .metric-label { font-size: 12px; color: #94a3b8; margin-bottom: 8px; }
      .metric-value { font-size: 26px; font-weight: 700; color: #f8fafc; }
      .tree-frame { padding: 18px 20px; overflow: hidden; }
      .preview-wrapper { height: 800px; overflow: auto; padding: 18px 20px; }
      .preview-frame { width: 100%; height: 100%; border: none; background: white; }
      .summary-card { background: #0f172a; border: 1px solid #1f2937; border-radius: 14px; padding: 16px; margin-bottom: 12px; color: #e2e8f0; }
    </style>
    <div class="split-pane" id="splitPane">
      <div class="pane left-pane" id="leftPane">
        <div class="section-header">Snapshot Summary</div>
        <div class="metrics-grid">
          <div class="metric-card"><div class="metric-label">Total Links</div><div class="metric-value">__TOTAL_LINKS__</div></div>
          <div class="metric-card"><div class="metric-label">Total Buttons</div><div class="metric-value">__TOTAL_BUTTONS__</div></div>
          <div class="metric-card"><div class="metric-label">Total Forms</div><div class="metric-value">__TOTAL_FORMS__</div></div>
          <div class="metric-card"><div class="metric-label">Total Tables</div><div class="metric-value">__TOTAL_TABLES__</div></div>
          <div class="metric-card"><div class="metric-label">Total Inputs</div><div class="metric-value">__TOTAL_INPUTS__</div></div>
        </div>
        <div class="section-header">DOM Structure</div>
        <div class="tree-frame">__DOM_HTML__</div>
      </div>
      <div class="dragbar" id="dragbar"></div>
      <div class="pane right-pane">
        <div class="section-header">Website Preview</div>
        <div style="height:800px; overflow:auto; padding: 0; background: #0f172a;">
          <iframe class="preview-frame" src="__URL__" sandbox="allow-same-origin allow-scripts allow-popups allow-forms"></iframe>
        </div>
      </div>
    </div>
    <script>
      const dragbar = document.getElementById('dragbar');
      const leftPane = document.getElementById('leftPane');
      const splitPane = document.getElementById('splitPane');
      let dragging = false;
      dragbar.addEventListener('mousedown', () => dragging = true);
      window.addEventListener('mouseup', () => dragging = false);
      window.addEventListener('mousemove', (e) => {
        if (!dragging) return;
        const rect = splitPane.getBoundingClientRect();
        let width = e.clientX - rect.left;
        if (width < 320) width = 320;
        if (width > rect.width - 420) width = rect.width - 420;
        leftPane.style.width = width + 'px';
      });
    </script>
    """
    return (
        template
        .replace("__TOTAL_LINKS__", str(metrics.get('total_links', 0)))
        .replace("__TOTAL_BUTTONS__", str(metrics.get('total_buttons', 0)))
        .replace("__TOTAL_FORMS__", str(metrics.get('total_forms', 0)))
        .replace("__TOTAL_TABLES__", str(metrics.get('total_tables', 0)))
        .replace("__TOTAL_INPUTS__", str(metrics.get('total_inputs', 0)))
        .replace("__DOM_HTML__", dom_html)
        .replace("__URL__", url)
    )


def render_compare_page(history, compare_result):
    old_options = [(item['id'], f"{item['id']} — {item['url']}") for item in history]
    selected_left = st.session_state.get('compare_left') or (old_options[0][0] if old_options else None)
    selected_right = st.session_state.get('compare_right') or (old_options[1][0] if len(old_options) > 1 else None)

    st.markdown(
        """
        <style>
          .compare-section { background: #0f172a; border: 1px solid #475569; border-radius: 18px; padding: 18px; margin-bottom: 18px; }
          .compare-header { color: #f8fafc; font-size: 18px; font-weight: 700; margin-bottom: 12px; }
          .stSelectbox>div>div>div>select, .stButton>button { background-color: #1f2937 !important; color: #f8fafc !important; border: 1px solid #475569 !important; }
          .stButton>button:hover { background-color: #334155 !important; }
          .stMetric { background: #111827 !important; border: 1px solid #334155 !important; border-radius: 16px !important; color: #f8fafc !important; }
          .stMetricValue { color: #dbeafe !important; }
          .stMetricLabel { color: #94a3b8 !important; }
          .streamlit-expanderHeader { background: #0f172a !important; border: 1px solid #334155 !important; border-radius: 14px !important; }
          .streamlit-expanderContent { background: #111827 !important; border: 1px solid #334155 !important; border-radius: 0 0 14px 14px !important; }
          .stTable td, .stTable th { background-color: #0f172a !important; color: #e2e8f0 !important; border-color: #334155 !important; }
          .stTable tbody tr:nth-child(odd) td { background: #111827 !important; }
          .stTable tbody tr:nth-child(even) td { background: #0f172a !important; }
          .compare-cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }
          .compare-metric-card { background: #111827; border: 1px solid #334155; border-radius: 18px; padding: 20px; }
          .compare-metric-label { color: #94a3b8; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 10px; }
          .compare-metric-value { color: #dbeafe; font-size: 38px; font-weight: 800; line-height: 1; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    with cols[0]:
        left_choice = st.selectbox("Old Snapshot ID", [opt[0] for opt in old_options], format_func=lambda x: dict(old_options).get(x, x), index=0 if old_options else 0, key="compare_left")
    with cols[1]:
        right_choice = st.selectbox("New Snapshot ID", [opt[0] for opt in old_options], format_func=lambda x: dict(old_options).get(x, x), index=1 if len(old_options) > 1 else 0, key="compare_right")

    _, button_col2 = st.columns([1, 3])
    with button_col2:
        if st.button("Compare Snapshots"):
            compare_snapshots(left_choice, right_choice)

    if compare_result:
        metrics = compare_result.get('metrics', {})
        st.markdown(
            '<div class="compare-section">'
            '<div class="compare-header">Comparison results</div>'
            '<div class="compare-cards">'
            f'<div class="compare-metric-card"><div class="compare-metric-label">Added nodes</div><div class="compare-metric-value">{metrics.get("added_nodes", 0)}</div></div>'
            f'<div class="compare-metric-card"><div class="compare-metric-label">Removed nodes</div><div class="compare-metric-value">{metrics.get("removed_nodes", 0)}</div></div>'
            f'<div class="compare-metric-card"><div class="compare-metric-label">Changed nodes</div><div class="compare-metric-value">{metrics.get("changed_nodes", 0)}</div></div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        with st.expander("Added Nodes", expanded=True):
            st.table(compare_result.get('added_nodes', []))
        with st.expander("Removed Nodes", expanded=False):
            st.table(compare_result.get('removed_nodes', []))
        with st.expander("Changed Nodes", expanded=False):
            st.table(compare_result.get('changed_nodes', []))


def render_history_sidebar(history):
    st.sidebar.subheader("Snapshot history")
    if not history:
        st.sidebar.write("No snapshots yet.")
        return
    for snap in history[:12]:
        if st.sidebar.button(f"{snap['id']} — {snap['url']}", key=f"load_{snap['id']}"):
            load_snapshot(snap['id'])
    st.sidebar.button("Refresh history", on_click=lambda: fetch_history(force=True))


history = fetch_history()
render_history_sidebar(history)

st.title("Webpage Analyzer Platform")

if st.session_state.page == "Analyze":
    st.subheader("Analyze")
    left, right = st.columns([3, 1])
    with left:
        url_input = st.text_input("URL to analyze", value=st.session_state.get('last_url', ''), placeholder="https://example.com")
        if st.button("Analyze"):
            if not url_input:
                st.error("Please enter a URL.")
            else:
                st.session_state.last_url = url_input
                analyze_url(url_input)

    if st.session_state.snapshot:
        components.html(render_analyze_html(st.session_state.snapshot), height=900)
    else:
        st.info("Run an analysis or load a snapshot from the sidebar.")

elif st.session_state.page == "Compare":
    st.subheader("Compare")
    if not history:
        st.warning("No history available to compare.")
    else:
        render_compare_page(history, st.session_state.compare_result)

