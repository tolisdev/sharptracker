import streamlit as st
import pandas as pd

from data.data_layer import clear_user_data


def render_settings():
    df_meta = st.session_state.meta_df

    st.title("User Configuration")
    st.info("Edit your personal lists. Changes only affect your account.")

    cfg1, cfg2, cfg3, cfg4, cfg5 = st.columns(5)

    s_v = cfg1.text_area(
        "Sports",
        "\n".join([str(x) for x in df_meta["Sports"].dropna().tolist()]),
        height=350,
    )
    l_v = cfg2.text_area(
        "Leagues",
        "\n".join([str(x) for x in df_meta["Leagues"].dropna().tolist()]),
        height=350,
    )
    b_v = cfg3.text_area(
        "Bookies",
        "\n".join([str(x) for x in df_meta["Bookies"].dropna().tolist()]),
        height=350,
    )
    t_v = cfg4.text_area(
        "Bet Types",
        "\n".join([str(x) for x in df_meta["Types"].dropna().tolist()]),
        height=350,
    )
    tip_v = cfg5.text_area(
        "Tipsters",
        "\n".join([str(x) for x in df_meta["Tipsters"].dropna().tolist()])
        if "Tipsters" in df_meta.columns else "",
        height=350,
    )

    if st.button("Apply Config Updates", type="primary"):
        u_meta = {
            "Sports":   [x.strip() for x in s_v.split("\n") if x.strip()],
            "Leagues":  [x.strip() for x in l_v.split("\n") if x.strip()],
            "Bookies":  [x.strip() for x in b_v.split("\n") if x.strip()],
            "Types":    [x.strip() for x in t_v.split("\n") if x.strip()],
            "Tipsters": [x.strip() for x in tip_v.split("\n") if x.strip()],
        }
        st.session_state.meta_df = pd.DataFrame.from_dict(
            u_meta, orient="index"
        ).transpose()
        st.session_state.unsaved_count += 1
        st.success("Configuration updated locally. Push to cloud to persist.")

    st.divider()
    st.subheader("Danger Zone")
    st.warning(
        "This permanently deletes all wagers and bankroll activity for your account. "
        "Your settings lists will be kept."
    )
    confirm_delete = st.checkbox(
        "I understand this will erase all logged user data except settings."
    )
    if st.button(
        "Delete All User Data (Keep Settings)",
        disabled=not confirm_delete,
    ):
        clear_user_data()
