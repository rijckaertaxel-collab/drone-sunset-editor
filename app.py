import streamlit as st
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import math
import uuid
import requests
from io import BytesIO
from supabase import create_client, Client

# --- 1. PAGINA INSTELLINGEN & CSS STYLING ---
st.set_page_config(page_title="DroneLuxe Editor & Cloud", page_icon="☁️", layout="wide")

# Professionele CSS om de look & feel direct te upgraden naar een moderne SaaS-tool
st.markdown("""
<style>
    /* Styling voor de navigatiebalk */
    .nav-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #1E1E24;
        padding: 10px 20px;
        border-radius: 10px;
        margin-bottom: 25px;
        border: 1px solid #333;
    }
    .nav-title {
        font-size: 22px;
        font-weight: bold;
        color: #00C9FF;
        text-decoration: none;
    }
    .nav-user {
        font-size: 14px;
        color: #AEB2C6;
    }
    
    /* Grote heldere knoppen */
    div.stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    /* Cards voor functies op de landingpage */
    .feature-card {
        background-color: #151518;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #222;
        margin-bottom: 15px;
    }
    .feature-card h3 {
        color: #00C9FF !important;
        margin-top: 0;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SUPABASE CONNECTIE ---
if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
    st.error("❌ De Secrets (SUPABASE_URL of SUPABASE_KEY) zijn niet gevonden in je Streamlit Dashboard!")
    st.stop()

if 'supabase' not in st.session_state:
    st.session_state.supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

if 'user' not in st.session_state:
    st.session_state.user = None

if 'session_data' not in st.session_state:
    st.session_state.session_data = None

# Pagina status bijhouden (om te navigeren tussen Home, Login, Editor, Galerij, Account)
if 'page' not in st.session_state:
    st.session_state.page = "Home"

# Sessie herstellen indien aanwezig
if st.session_state.session_data is not None:
    try:
        st.session_state.supabase.auth.set_session(
            st.session_state.session_data["access_token"],
            st.session_state.session_data["refresh_token"]
        )
    except Exception:
        pass

# --- 3. DYNAMISCHE NAVIGATIEBALK (BOVENAAN) ---
def render_navbar():
    if st.session_state.user is None:
        # NAVIGATIE NIET INGELOGD
        col_logo, col_buttons = st.columns([3, 1])
        with col_logo:
            st.markdown("<div style='padding-top: 10px;'><span style='font-size: 24px; font-weight: 800; color: #00C9FF;'>☁️ DroneLuxe</span> <span style='color: #666;'>| Premium Photo Cloud</span></div>", unsafe_allow_html=True)
        with col_buttons:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Log In", key="nav_login", use_container_width=True):
                    st.session_state.page = "Login"
                    st.rerun()
            with c2:
                if st.button("Registreren", key="nav_register", use_container_width=True, type="primary"):
                    st.session_state.page = "Register"
                    st.rerun()
    else:
        # NAVIGATIE WEL INGELOGD
        col_logo, col_menu, col_user = st.columns([2, 4, 2])
        with col_logo:
            st.markdown("<div style='padding-top: 10px;'><span style='font-size: 24px; font-weight: 800; color: #00C9FF;'>☁️ DroneLuxe</span></div>", unsafe_allow_html=True)
        with col_menu:
            # Horizontale pagina selectie
            selected = st.segmented_control(
                "Navigatie",
                options=["✨ Editor", "🖼️ Mijn Galerij", "👤 Mijn Account"],
                default="✨ Editor",
                label_visibility="collapsed"
            )
            if selected == "✨ Editor" and st.session_state.page != "Editor":
                st.session_state.page = "Editor"
                st.rerun()
            elif selected == "🖼️ Mijn Galerij" and st.session_state.page != "Gallery":
                st.session_state.page = "Gallery"
                st.rerun()
            elif selected == "👤 Mijn Account" and st.session_state.page != "Account":
                st.session_state.page = "Account"
                st.rerun()
        with col_user:
            st.markdown(f"<div style='text-align: right; padding-top: 5px; font-size: 13px; color: #aaa;'>Ingelogd als:<br><b>{st.session_state.user.email}</b></div>", unsafe_allow_html=True)
            if st.button("Uitloggen", key="nav_logout", use_container_width=True):
                st.session_state.supabase.auth.sign_out()
                st.session_state.user = None
                st.session_state.session_data = None
                st.session_state.page = "Home"
                st.rerun()
    st.write("---")

render_navbar()

# --- FOTO BEWERKINGSHULPMIDDELEN ---
def crop_around_center(image, angle):
    if abs(angle) < 0.1:
        return image
    w, h = image.size
    angle_rad = math.radians(abs(angle))
    sin_a = math.sin(angle_rad)
    cos_a = math.cos(angle_rad)
    if w >= h:
        dest_w = (w * cos_a - h * sin_a) / (cos_a**2 - sin_a**2)
        dest_h = (h * cos_a - w * sin_a) / (cos_a**2 - sin_a**2)
    else:
        dest_w = (h * cos_a - w * sin_a) / (cos_a**2 - sin_a**2)
        dest_h = (w * cos_a - h * sin_a) / (cos_a**2 - sin_a**2)
    dest_w = int(min(w, max(10, dest_w)) * 0.95)
    dest_h = int(min(h, max(10, dest_h)) * 0.95)
    left = (w - dest_w) // 2
    top = (h - dest_h) // 2
    right = left + dest_w
    bottom = top + dest_h
    return image.crop((left, top, right, bottom))

def apply_smart_hdr(img, shadow_boost=1.35, saturation=1.3):
    img = img.convert("RGB")
    gray = img.convert("L")
    shadow_mask = ImageOps.invert(gray).filter(ImageFilter.GaussianBlur(radius=20))
    boosted_img = Image.eval(img, lambda x: min(255, int(x * shadow_boost)))
    hdr_img = Image.composite(boosted_img, img, shadow_mask)
    hdr_img = ImageEnhance.Color(hdr_img).enhance(saturation)
    hdr_img = ImageEnhance.Contrast(hdr_img).enhance(1.05)
    return hdr_img

def apply_preset(img, preset_name):
    if preset_name == "HDR Natural (Herstel Schaduwen) 🍃":
        return apply_smart_hdr(img, shadow_boost=1.4, saturation=1.25)
    elif preset_name == "Golden Hour Sunset 🌅":
        hdr = apply_smart_hdr(img, shadow_boost=1.3, saturation=1.45)
        r, g, b = hdr.split()
        r = r.point(lambda i: min(255, int(i * 1.12)))
        g = g.point(lambda i: min(255, int(i * 1.02)))
        return Image.merge("RGB", (r, g, b))
    elif preset_name == "Cinematic Sky ☁️":
        hdr = apply_smart_hdr(img, shadow_boost=1.45, saturation=1.15)
        r, g, b = hdr.split()
        b = b.point(lambda i: min(255, int(i * 1.03)))
        return Image.merge("RGB", (r, g, b))
    return img


# --- 4. PAGINA ROUTING & LOGICA ---

# ==================== PAGINA: HOME (LANDINGPAGE) ====================
if st.session_state.page == "Home":
    st.markdown("""
    <div style='text-align: center; padding: 40px 0;'>
        <h1 style='font-size: 50px; font-weight: 900; background: linear-gradient(45deg, #00C9FF, #92FE9D); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>Breng je Drone Foto's tot Leven</h1>
        <p style='font-size: 20px; color: #AEB2C6; max-width: 700px; margin: 20px auto;'>De ultieme online foto-editor speciaal ontworpen voor drone- en zonsondergangfotografie. Bewerk razendsnel, corrigeer de horizon en bewaar alles veilig in jouw persoonlijke cloud.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Prachtige side-by-side preview sectie
    col_demo1, col_demo2 = st.columns(2)
    with col_demo1:
        st.markdown("""
        <div class="feature-card">
            <h3>✨ Slimme HDR & Sunset Presets</h3>
            <p>Herstel automatisch donkere schaduwen en geef je luchten die diepe, warme gouden gloed die ze verdienen zonder kwaliteitsverlies.</p>
        </div>
        <div class="feature-card">
            <h3>📐 Automatisch Gecropte Horizon</h3>
            <p>Geen schuine horizon meer. Roteer je foto's soepel; onze slimme editor snijdt de zwarte randen er direct en automatisch voor je af.</p>
        </div>
        <div class="feature-card">
            <h3>☁️ Jouw Persoonlijke Cloud</h3>
            <p>Sla je resultaten rechtstreeks op in je eigen, afgeschermde account. Altijd en overal direct downloadbaar vanaf elk apparaat.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Direct gratis starten 🚀", use_container_width=True, type="primary"):
            st.session_state.page = "Register"
            st.rerun()

    with col_demo2:
        st.subheader("📸 Preview van onze filters")
        # Toon een mooie mock-up of default foto ter illustratie
        st.info("Log in om je eigen drone-foto's te uploaden en te bewerken!")
        try:
            # We laden een mooie placeholder zonsondergang in
            response = requests.get("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80")
            img_placeholder = Image.open(BytesIO(response.content))
            
            preset_demo = apply_preset(img_placeholder, "Golden Hour Sunset 🌅")
            
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                st.caption("Origineel (Onbewerkt)")
                st.image(img_placeholder, use_container_width=True)
            with c_p2:
                st.caption("Golden Hour Sunset Filter ✨")
                st.image(preset_demo, use_container_width=True)
        except Exception:
            st.image("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=600&q=80", use_container_width=True)


# ==================== PAGINA: LOGIN / REGISTREREN ====================
elif st.session_state.page in ["Login", "Register"]:
    st.markdown(f"<h2 style='text-align: center;'>{'Aanmelden bij' if st.session_state.page == 'Login' else 'Account aanmaken voor'} DroneLuxe Cloud</h2>", unsafe_allow_html=True)
    
    col_auth_box, _ = st.columns([2, 2])
    with col_auth_box:
        with st.form("auth_form"):
            email = st.text_input("E-mailadres", placeholder="naam@voorbeeld.nl")
            password = st.text_input("Wachtwoord (minimaal 6 tekens)", type="password")
            
            submit_label = "Inloggen" if st.session_state.page == "Login" else "Account aanmaken"
            submitted = st.form_submit_button(submit_label, use_container_width=True, type="primary")
            
            if submitted:
                if not email or not password:
                    st.warning("Vul alle velden in.")
                elif len(password) < 6:
                    st.warning("Wachtwoord moet minimaal 6 tekens bevatten.")
                else:
                    if st.session_state.page == "Login":
                        try:
                            response = st.session_state.supabase.auth.sign_in_with_password({"email": email, "password": password})
                            st.session_state.user = response.user
                            st.session_state.session_data = {
                                "access_token": response.session.access_token,
                                "refresh_token": response.session.refresh_token
                            }
                            st.success("Succesvol ingelogd!")
                            st.session_state.page = "Editor"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Inloggen mislukt: {e}")
                    else:
                        try:
                            response = st.session_state.supabase.auth.sign_up({"email": email, "password": password})
                            st.success("Account geregistreerd! Je kunt nu direct inloggen.")
                            st.session_state.page = "Login"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Registratie mislukt: {e}")
        
        # FIX: variant="secondary" is hier verwijderd om de crash te voorkomen!
        if st.session_state.page == "Login":
            if st.button("Nog geen account? Registreer hier", use_container_width=True):
                st.session_state.page = "Register"
                st.rerun()
        else:
            if st.button("Al een account? Log hier in", use_container_width=True):
                st.session_state.page = "Login"
                st.rerun()
# ==================== PAGINA: EDITOR (WEL INGELOGD) ====================
elif st.session_state.page == "Editor":
    st.subheader("⚡ Premium Photo Editor")
    
    uploaded_file = st.file_uploader("Sleep je drone-foto hiernaartoe...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        original_image = Image.open(uploaded_file)
        
        col_settings_1, col_settings_2 = st.columns(2)
        with col_settings_1:
            preset = st.selectbox("Selecteer Preset Filter:", ["HDR Natural (Herstel Schaduwen) 🍃", "Golden Hour Sunset 🌅", "Cinematic Sky ☁️", "Standaard (Geen filter)"])
        with col_settings_2:
            angle_input = st.slider("Horizon Waterpas Roteren:", min_value=-15.0, max_value=15.0, value=0.0, step=0.5)

        processed_image = apply_preset(original_image, preset)
        if angle_input != 0.0:
            rotated = processed_image.rotate(angle_input, resample=Image.Resampling.BICUBIC, expand=False)
            processed_image = crop_around_center(rotated, angle_input)

        st.write("---")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Origineel 📸")
            st.image(original_image, use_container_width=True)
        with col2:
            st.subheader("Resultaat ✨")
            st.image(processed_image, use_container_width=True)
            
            # Sla tijdelijk op voor download / upload
            processed_image.save("temp.jpg", "JPEG", quality=95)
            with open("temp.jpg", "rb") as file:
                file_bytes = file.read()
                
            sub_c1, sub_c2 = st.columns(2)
            with sub_c1:
                st.download_button("Lokaal Opslaan 📥", data=file_bytes, file_name="drone_edited.jpg", mime="image/jpeg", use_container_width=True)
            with sub_c2:
                if st.button("Save to Cloud ☁️", use_container_width=True, type="primary"):
                    with st.spinner("Opslaan in cloud..."):
                        try:
                            if st.session_state.session_data:
                                st.session_state.supabase.auth.set_session(
                                    st.session_state.session_data["access_token"],
                                    st.session_state.session_data["refresh_token"]
                                )
                            
                            file_name = f"{st.session_state.user.id}/{uuid.uuid4().hex}.jpg"
                            st.session_state.supabase.storage.from_("fotos").upload(
                                path=file_name, 
                                file=file_bytes, 
                                file_options={"content-type": "image/jpeg"}
                            )
                            st.success("Opgeslagen in je persoonlijke galerij!")
                            st.session_state.page = "Gallery"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fout bij opslaan: {e}")


# ==================== PAGINA: MIJN CLOUD GALERIJ (WEL INGELOGD) ====================
elif st.session_state.page == "Gallery":
    st.subheader("🖼️ Jouw Persoonlijke Cloud Galerij")
    st.write("Alleen jij hebt toegang tot deze beelden.")

    try:
        if st.session_state.session_data:
            st.session_state.supabase.auth.set_session(
                st.session_state.session_data["access_token"],
                st.session_state.session_data["refresh_token"]
            )
            
        user_folder = st.session_state.user.id
        files = st.session_state.supabase.storage.from_("fotos").list(user_folder)
        
        # Filter om verborgen systeembestanden of lege mappen te negeren
        image_files = [f for f in files if f['name'] and (f['name'].endswith('.jpg') or f['name'].endswith('.png') or f['name'].endswith('.jpeg'))]
        
        if not image_files:
            st.info("Je hebt nog geen foto's opgeslagen in je cloud. Ga naar de Editor en klik op 'Save to Cloud'!")
        else:
            cols = st.columns(3)
            for index, file_info in enumerate(image_files):
                file_name = file_info['name']
                full_path = f"{user_folder}/{file_name}"
                
                try:
                    # Genereer beveiligde, tijdelijke URL
                    sign_response = st.session_state.supabase.storage.from_("fotos").create_signed_url(full_path, 60)
                    image_url = sign_response['signedURL']
                    
                    col_index = index % 3
                    with cols[col_index]:
                        # Kaart-achtige weergave
                        st.markdown("<div class='feature-card'>", unsafe_allow_html=True)
                        st.image(image_url, use_container_width=True)
                        
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            # Downloadknop
                            response = requests.get(image_url)
                            if response.status_code == 200:
                                st.download_button(
                                    label="Download 📥",
                                    data=response.content,
                                    file_name=f"cloud_{file_name}",
                                    mime="image/jpeg",
                                    key=f"dl_{file_name}_{index}",
                                    use_container_width=True
                                )
                        with btn_col2:
                            # Verwijderknop
                            if st.button("Wissen 🗑️", key=f"del_{file_name}_{index}", use_container_width=True):
                                with st.spinner("Verwijderen..."):
                                    st.session_state.supabase.storage.from_("fotos").remove([full_path])
                                    st.success("Verwijderd!")
                                    st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Fout bij laden: {e}")
    except Exception as e:
        st.error(f"Kan je galerij niet laden: {e}")


# ==================== PAGINA: MIJN ACCOUNT (WEL INGELOGD) ====================
elif st.session_state.page == "Account":
    st.subheader("👤 Mijn DroneLuxe Account")
    
    st.markdown("<div class='feature-card'>", unsafe_allow_html=True)
    st.write(f"**E-mailadres:** {st.session_state.user.email}")
    st.write(f"**Unieke Gebruikers ID (UUID):** `{st.session_state.user.id}`")
    st.write(f"**Account Status:** Geverifieerd Actief")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.info("Binnenkort kun je hier ook je wachtwoord wijzigen of je accountinstellingen aanpassen!")
