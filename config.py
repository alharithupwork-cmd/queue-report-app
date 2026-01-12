
# config.py

CONFIG = {
    # --------------------
    # Login page selectors (edit to match your login form)
    # --------------------
    "login": {
        # If your site shows a username/password form:
        "username_selector": "input[name='username']",
        "password_selector": "input[name='password']",
        "submit_selector": "button[type='submit']",

        # Optional: an element that only appears when logged in
        # e.g., user avatar, navbar item
        "post_login_check_selector": "#userAvatar, .nav-user, .profile-menu",
        # Timeouts
        "login_timeout_ms": 20000,
    },

    # --------------------
    # Queues page selectors
    # --------------------
    # Container that holds all queue tabs (e.g., <ul id="queueTabs">)
    "queue_tab_container_selector": "#queueTabs",
    # The clickable tab item inside the container (e.g., li > a)
    "queue_tab_item_selector": "li > a",

    # The main table for queue records
    "table_selector": "table#queueTable",
    "table_header_selector": "table#queueTable thead tr th",
    "table_row_selector": "table#queueTable tbody tr",
    "table_cell_selector": "td",

    # Pagination (if the queue uses paging)
    "next_button_selector": "a.next, button.next",
    "next_button_disabled_class": "disabled",

    # Optional: if pagination uses text content instead of disabled class
    "next_button_texts": ["Next", "»", "›"],

    # Map visible table headers to normalized keys
    "columns_map": {
        "Case ID": "case_id",
        "Category": "category",
        "Subcategory": "subcategory",
        # Add any other headers you need:
        # "Status": "status",
        # "Owner": "owner",
        # "Created": "created",
    },

    # General waits/timeouts
    "page_load_timeout_ms": 20000,
    "network_idle_timeout_ms": 1000,
}
