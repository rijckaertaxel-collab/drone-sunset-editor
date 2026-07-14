import streamlit as st
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import math
import uuid
from supabase import create_client, Client

# --- 1. SUPABASE CONNECTIE CONTROLE ---
@st.cache_resource
def init_connection():
    # Controleer of de secrets überhaupt bestaan
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
        st.error("❌ De Secrets (SUPABASE_URL of SUPABASE_KEY) zijn niet gevonden in je Streamlit Dashboard!")
        st.info("Ga naar share.streamlit.io -> Drie puntjes naast je app -> Settings -> Secrets en plak ze daar erin.")
        st.stop()
        
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error(f"⚠️ Verbinding met Supabase mislukt tijdens het opstarten: {e}")
    st.stop()

# --- 2. SESSIE BEHEREN ---
if 'user' not in st.session_state:
    st.session_state.user = None

# Pagina instellingen
st.set_page_config(page_title="Drone Photo Editor Cloud", page_icon="☁️", layout="centered")
st.title("☁️ Drone & Sunset Editor (Cloud)")

# --- 3. INLOGSYSTEEM MET EXACTE FOUTMELDINGEN ---
if st.session_state.user is None:
    st.info("Log in of maak gratis een account aan.")
    
    with st.container():
        email = st.text_input("E-mailadres", placeholder="voorbeeld@email.com")
        password = st.text_input("Wachtwoord (minimaal 6 tekens)", type="password")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Log in", use_container_width=True):
                if not email or not password:
                    st.warning("Vul alstublieft beide velden in.")
                else:
                    try:
                        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = response.user
                        st.success("Succesvol ingelogd!")
                        st.rerun()
                    except Exception as e:
                        # Dit laat de ECHTE fout van Supabase zien:
                        st.error(f"Fout bij inloggen: {e}")
        with c2:
            if st.button("Registreer", use_container_width=True):
                if not email or not password:
                    st.warning("Vul alstublieft beide velden in.")
                elif len(password) < 6:
                    st.warning("Je wachtwoord moet minimaal 6 tekens lang zijn!")
                else:
                    try:
                        response = supabase.auth.sign_up({"email": email, "password": password})
                        st.success("Account aangemaakt! Probeer nu in te loggen.")
                    except Exception as e:
                        # Dit laat de ECHTE fout van Supabase zien bij registratie:
                        st.error(f"Fout bij registreren: {e}")
    st.stop()

# --- GEBRUIKER INGEILOGD ---
c1, c2 = st.columns([3, 1])
with c1:
    st.success(f"👋 Welkom, {st.session_state.user.email}")
with c2:
    if st.button("Uitloggen", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

st.write("---")

# --- FOTO EDITOR FUNCTIES ---
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

uploaded_file = st.file_uploader("Upload je foto...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    original_image = Image.open(uploaded_file)
    st.write("---")
    col_settings_1, col_settings_2 = st.columns(2)
    with col_settings_1:
        preset = st.selectbox("Kies een preset style:", ["HDR Natural (Herstel Schaduwen) 🍃", "Golden Hour Sunset 🌅", "Cinematic Sky ☁️", "Standaard (Geen filter)"])
    with col_settings_2:
        angle_input = st.slider("Horizon roteren:", min_value=-15.0, max_value=15.0, value=0.0, step=0.5)

    processed_image = apply_preset(original_image, preset)
    if angle_input != 0.0:
        rotated = processed_image.rotate(angle_input, resample=Image.Resampling.BICUBIC, expand=False)
        processed_image = crop_around_center(rotated, angle_input)

    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Origineel")
        st.image(original_image, use_container_width=True)
    with col2:
        st.subheader("Verbeterd ✨")
        st.image(processed_image, use_container_width=True)
        
        processed_image.save("temp.jpg", "JPEG", quality=95)
        with open("temp.jpg", "rb") as file:
            file_bytes = file.read()
            
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1:
            st.download_button("Lokaal Downloaden 📥", data=file_bytes, file_name="drone_edited.jpg", mime="image/jpeg")
        with sub_c2:
            if st.button("Save to Cloud ☁️"):
                with st.spinner("Bezig met opslaan..."):
                    try:
                        file_name = f"{st.session_state.user.id}/{uuid.uuid4().hex}.jpg"
                        supabase.storage.from_("fotos").upload(path=file_name, file=file_bytes, file_options={"content-type": "image/jpeg"})
                        public_url = supabase.storage.from_("fotos").get_public_url(file_name)
                        st.success("Opgeslagen!")
                        st.markdown(f"[Bekijk je cloud-foto hier]({public_url})")
                    except Exception as e:
                        st.error(f"Fout bij opslaan: {e}")
