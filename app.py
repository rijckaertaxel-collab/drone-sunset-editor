import streamlit as st
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import numpy as np
import math
from skimage.transform import radon

# Pagina instellingen
st.set_page_config(page_title="Smart Drone Photo Editor", page_icon="🛸", layout="centered")

st.title("🛸 Smart Drone Photo Editor")
st.write("Professionele HDR-presets met een slimme horizon-correctie!")

# --- INTELLIGENTE HORIZON DETECTIE (Focus op het midden) ---
def detect_horizon_angle(pil_img):
    try:
        # We snijden de bovenkant (lucht/wolken) en onderkant (grond) weg om alleen de horizonlijn te scannen
        w, h = pil_img.size
        middle_band = pil_img.crop((0, int(h * 0.3), w, int(h * 0.7)))
        
        img_gray = middle_band.convert("L").resize((256, 128), Image.Resampling.BILINEAR)
        img_arr = np.array(img_gray) - np.mean(img_gray)
        
        tested_angles = np.linspace(-10, 10, 80, endpoint=False)
        sinogram = radon(img_arr, theta=tested_angles)
        
        variances = np.var(sinogram, axis=0)
        best_angle_idx = np.argmax(variances)
        detected_angle = tested_angles[best_angle_idx]
        
        return -float(detected_angle)
    except:
        return 0.0

# Waterdichte Auto-Crop na rotatie
def crop_around_center(image, angle):
    if abs(angle) < 0.2:
        return image
        
    w, h = image.size
    angle_rad = math.radians(abs(angle))
    
    # Bereken de veilige binnengrenzen om zwarte randen te vermijden
    sin_a = math.sin(angle_rad)
    cos_a = math.cos(angle_rad)
    
    if w >= h:
        dest_w = (w * cos_a - h * sin_a) / (cos_a**2 - sin_a**2)
        dest_h = (h * cos_a - w * sin_a) / (cos_a**2 - sin_a**2)
    else:
        dest_w = (h * cos_a - w * sin_a) / (cos_a**2 - sin_a**2)
        dest_h = (w * cos_a - h * sin_a) / (cos_a**2 - sin_a**2)
        
    # Extra veiligheidsmarge (95% van de berekende crop) om afrondingsfouten te voorkomen
    dest_w = int(min(w, max(10, dest_w)) * 0.95)
    dest_h = int(min(h, max(10, dest_h)) * 0.95)
    
    left = (w - dest_w) // 2
    top = (h - dest_h) // 2
    right = left + dest_w
    bottom = top + dest_h
    
    return image.crop((left, top, right, bottom))

# --- HDR PRESETS (BEHOUDEN & VERBETERD) ---
def apply_smart_hdr(img, shadow_boost=1.35, saturation=1.3):
    img = img.convert("RGB")
    gray = img.convert("L")
    
    # Schaduwmasker maken en vervagen
    shadow_mask = ImageOps.invert(gray)
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=20))
    
    # Schaduwen oplichten
    boosted_img = Image.eval(img, lambda x: min(255, int(x * shadow_boost)))
    hdr_img = Image.composite(boosted_img, img, shadow_mask)
    
    # Kleuren en contrast herstellen
    hdr_img = ImageEnhance.Color(hdr_img).enhance(saturation)
    hdr_img = ImageEnhance.Contrast(hdr_img).enhance(1.08)
    
    return hdr_img

def apply_preset(img, preset_name):
    if preset_name == "HDR Natural (Herstel Schaduwen) 🍃":
        return apply_smart_hdr(img, shadow_boost=1.45, saturation=1.25)
    elif preset_name == "Golden Hour Sunset 🌅":
        hdr = apply_smart_hdr(img, shadow_boost=1.35, saturation=1.45)
        r, g, b = hdr.split()
        r = r.point(lambda i: min(255, int(i * 1.15)))
        g = g.point(lambda i: min(255, int(i * 1.03)))
        return Image.merge("RGB", (r, g, b))
    elif preset_name == "Cinematic Sky ☁️":
        hdr = apply_smart_hdr(img, shadow_boost=1.5, saturation=1.15)
        r, g, b = hdr.split()
        b = b.point(lambda i: min(255, int(i * 1.04)))
        return Image.merge("RGB", (r, g, b))
    return img

# --- INTERFACE ---
uploaded_file = st.file_uploader("Upload je dronefoto...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Laad de foto in het geheugen
    original_image = Image.open(uploaded_file)
    
    # Bereken op de achtergrond alvast de gok van de AI voor de horizon
    if 'detected_angle' not in st.session_state or st.session_state.get('last_file') != uploaded_file.name:
        st.session_state['detected_angle'] = detect_horizon_angle(original_image)
        st.session_state['last_file'] = uploaded_file.name

    st.write("---")
    st.subheader("Instellingen")
    
    col_settings_1, col_settings_2 = st.columns(2)
    
    with col_settings_1:
        preset = st.selectbox(
            "Kies een preset style:",
            ["HDR Natural (Herstel Schaduwen) 🍃", "Golden Hour Sunset 🌅", "Cinematic Sky ☁️", "Standaard (Geen filter)"]
        )
        
    with col_settings_2:
        # De slider begint automatisch op de hoek die de AI heeft berekend!
        # Als de AI er naast zit, kun je hem hier direct handmatig corrigeren.
        angle_input = st.slider(
            "Horizon handmatig bijsturen (AI gok is vooraf ingesteld):",
            min_value=-15.0,
            max_value=15.0,
            value=st.session_state['detected_angle'],
            step=0.5
        )
        
        # Knop om snel te resetten naar 0 (recht)
        if st.button("Reset rotatie naar 0°"):
            st.session_state['detected_angle'] = 0.0
            st.rerun()

    # 1. Pas de preset toe
    processed_image = apply_preset(original_image, preset)
    
    # 2. Pas de rotatie en de verbeterde auto-crop toe
    if angle_input != 0.0:
        rotated = processed_image.rotate(angle_input, resample=Image.Resampling.BICUBIC, expand=False)
        processed_image = crop_around_center(rotated, angle_input)

    # Resultaten tonen
    st.write("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Origineel")
        st.image(original_image, use_container_width=True)
        
    with col2:
        st.subheader("Verbeterd ✨")
        st.image(processed_image, use_container_width=True)
        
        # Opslaan voor download
        processed_image.save("edited_output.jpg", "JPEG", quality=95)
        with open("edited_output.jpg", "rb") as file:
            st.download_button(
                label="Download Verbeterde Foto 📥",
                data=file,
                file_name="drone_edited.jpg",
                mime="image/jpeg"
            )
