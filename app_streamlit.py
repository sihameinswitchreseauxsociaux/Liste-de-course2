# app_streamlit.py
import uuid
import os
import streamlit as st
from supabase import create_client

# --- Supabase client depuis Streamlit secrets ou variables d'environnement ---
SUPABASE_URL = st.secrets.get("SUPABASE_URL") if st.secrets else os.environ.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY") if st.secrets else os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.warning("Supabase keys manquantes. Configure SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY dans les secrets ou variables d'environnement.")
    SUPABASE = None
else:
    SUPABASE = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Navigation state ---
if "page" not in st.session_state:
    st.session_state.page = "home"

def go_to(page_name):
    st.session_state.page = page_name

# --- Styles ---
st.markdown(
    """
    <style>
    .tiles {display:flex;gap:12px;flex-wrap:wrap;margin-top:12px}
    .tile {background:#fff;border-radius:10px;padding:14px;flex:1;min-width:180px;box-shadow:0 4px 12px rgba(0,0,0,0.06);cursor:pointer;text-align:center}
    .tile h4 {margin:6px 0}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Header and layout ---
st.title("Organiser ses repas")
col1, col2 = st.columns([1,1.4])

with col1:
    try:
        st.image("maquette.png", use_column_width=True)
    except Exception:
        st.info("Placez 'maquette.png' dans le dossier de l'app pour afficher la maquette.")

with col2:
    st.markdown("### Navigation rapide")
    st.markdown("Clique sur une tuile pour ouvrir la page correspondante.")

    # Hidden Streamlit buttons triggered by HTML tiles
    if st.button("Recettes", key="btn_recettes"):
        go_to("recettes")
    if st.button("Planning", key="btn_planning"):
        go_to("planning")
    if st.button("Liste", key="btn_liste"):
        go_to("liste")

    st.markdown('<div class="tiles">', unsafe_allow_html=True)
    st.markdown('<div class="tile" onclick="document.querySelector(\'button[aria-label=btn_recettes]\').click()"><h4>📚 Recettes</h4><div>Voir et ajouter des recettes</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="tile" onclick="document.querySelector(\'button[aria-label=btn_planning]\').click()"><h4>📅 Planning</h4><div>Organiser vos repas</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="tile" onclick="document.querySelector(\'button[aria-label=btn_liste]\').click()"><h4>🛒 Liste de courses</h4><div>Gérer la liste</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# --- Helpers for Supabase storage ---
def upload_to_storage(filebytes, dest_path):
    if not SUPABASE:
        return None, "Supabase non configuré"
    try:
        res = SUPABASE.storage.from_("media").upload(dest_path, filebytes)
        # supabase-py returns dict with "error" on failure
        if isinstance(res, dict) and res.get("error"):
            return None, res["error"].get("message", "upload error")
        return dest_path, None
    except Exception as e:
        return None, str(e)

def create_signed_url(path, expires=3600):
    if not SUPABASE:
        return None
    try:
        signed = SUPABASE.storage.from_("media").create_signed_url(path, expires)
        if isinstance(signed, dict):
            return signed.get("signedURL")
        return None
    except Exception:
        return None

# --- Pages ---
if st.session_state.page == "home":
    st.info("Page d'accueil. Clique une tuile pour tester les pages.")

elif st.session_state.page == "recettes":
    st.header("Recettes")
    # Create recipe form
    with st.form("form_new_recipe", clear_on_submit=True):
        name = st.text_input("Nom de la recette")
        file = st.file_uploader("Image ou PDF", type=["png","jpg","jpeg","pdf"])
        submitted = st.form_submit_button("Créer la recette")
        if submitted and name:
            rid = str(uuid.uuid4())
            record = {"id": rid, "name": name}
            if file:
                ext = file.name.split(".")[-1].lower()
                path = f"recipes/{rid}/media.{ext}"
                uploaded_path, err = upload_to_storage(file.getvalue(), path)
                if err:
                    st.error(f"Erreur upload: {err}")
                else:
                    if ext == "pdf":
                        record["pdf_path"] = uploaded_path
                    else:
                        record["image_path"] = uploaded_path
            if SUPABASE:
                SUPABASE.table("recipes").insert(record).execute()
                st.success("Recette créée")
            else:
                st.info("Recette simulée (Supabase non configuré).")
    st.markdown("---")
    # List recipes
    st.subheader("Liste des recettes")
    rows = []
    if SUPABASE:
        resp = SUPABASE.table("recipes").select("*").order("created_at", desc=True).execute()
        rows = resp.data or []
    if rows:
        for r in rows:
            st.write(f"**{r.get('name')}**")
            imgp = r.get("image_path")
            pdfp = r.get("pdf_path")
            if imgp:
                url = create_signed_url(imgp)
                if url:
                    st.image(url, width=240)
            if pdfp:
                url = create_signed_url(pdfp)
                if url:
                    st.markdown(f"[Télécharger le PDF]({url})")
            st.markdown("---")
    else:
        st.info("Aucune recette pour le moment")

    if st.button("⬅️ Retour à l'accueil"):
        go_to("home")

elif st.session_state.page == "planning":
    st.header("Planning")
    st.write("Page de test pour le planning")
    days = ["lundi_midi","lundi_soir","mardi_midi","mardi_soir","mercredi_midi","mercredi_soir"]
    recipes = []
    if SUPABASE:
        resp = SUPABASE.table("recipes").select("id,name").execute()
        recipes = resp.data or []
    for d in days:
        cols = st.columns([2,1])
        cols[0].write(d)
        with cols[1]:
            if st.button(f"Assigner {d}", key=f"assign_{d}"):
                st.session_state[f"assign_target_{d}"] = True
        if st.session_state.get(f"assign_target_{d}"):
            sel = None
            if recipes:
                sel = st.selectbox("Choisir recette", options=[(r["id"], r["name"]) for r in recipes], format_func=lambda x: x[1])
            if st.button("Valider assignation", key=f"val_{d}"):
                if sel and SUPABASE:
                    SUPABASE.table("planning").insert({"week_label":"default","day_slot":d,"recipe_id":sel[0]}).execute()
                    st.success("Affecté")
                st.session_state[f"assign_target_{d}"] = False

    if st.button("⬅️ Retour à l'accueil"):
        go_to("home")

elif st.session_state.page == "liste":
    st.header("Liste de courses")
    st.write("Page de test pour la liste de courses")
    if st.button("⬅️ Retour à l'accueil"):
        go_to("home")

