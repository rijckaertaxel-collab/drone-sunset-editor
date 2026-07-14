import streamlit as st
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import numpy as np
import math
from skimage.transform import radon

# Pagina instellingen
st.set_page_config(page_title="Smart Drone Photo Editor", page_icon="🛸", layout="centered")

st.title("🛸 Smart Drone Photo Editor")
st.write("Corrigeert automatisch de horizon en herstelt te donkere schaduwen (HDR-effect)!")

# --- INTELLIGENTE HORIZON DETECTIE & AUTO-LEVEL ---
def detect_horizon_angle(pil_img):
    """
    Detecteert de horizonhoek met de Radon-transformatie.
    Dit zoekt naar de meest dominante rechte lijn in de foto.
    """
    # Maak een kleine, grijze versie van de foto voor snelle berekening
    img_gray = pil_img.convert("L").resize((256, 256), Image.Resampling.BILINEAR)
    img_arr = np.array(img_gray) - np.mean(img_gray) # Normaliseer
    
    # We testen hoeken rondom de horizon (-15 tot +15 graden)
    tested_angles = np.linspace(-15, 15, 120, endpoint=False)
    
    # Voer Radon-transformatie uit om rechte lijnen te detecteren
    sinogram = radon(img_arr, theta=tested_angles)
    
    # Zoek de hoek met de hoogste variantie (waar de scheidingslijn het scherpst is)
    variances = np.var(sinogram, axis=0)
    best_angle_idx = np.argmax(variances)
    detected_angle = tested_angles[best_angle_idx]
    
    # Corrigeer de richting van de hoek
    return -detected_angle

# Automatisch bijsnijden na rotatie
def crop_around_center(image, angle):
    if abs(angle) < 0.5:
        return image
        
    w, h = image.size
    angle_rad = math.radians(abs(angle))
    
    if w <= h:
        sin_a = math.sin(angle_rad)
        cos_a = math.cos(angle_rad)
        dest_w = w * cos_a - h * sin_a
        dest_h = h * cos_a - w * sin_a
    else:
        sin_a = math.sin(angle_rad)
        cos_a = math.cos(angle_rad)
        dest_w = w / (cos_a + sin_a * (w / h))
        dest_h = dest_w * (h / w)
        
    dest_w = max(10, min(w, int(dest_w)))
    dest_h = max(10, min(h, int(dest_h)))
    
    left = (w - dest_w) // 2
    top = (h - dest_h) // 2
    right = left + dest_w
    bottom = top + dest_h
    
    return image.crop((left, top, right, bottom))


# --- SLIMME HDR & PRESETS (HERSTELT SCHADUWEN) ---
def apply_smart_hdr(img, shadow_boost=1.35, highlight_protect=0.95, saturation=1.3):
    """
    In plaats van simpelweg contrast te pushen (wat schaduwen zwart maakt),
    lichten we hier selectief de donkere delen op (Shadow Recovery) en behouden we de lichten.
    """
    img = img.convert("RGB")
    
    # Splits kanalen
    r, g, b = img.split()
    
    # Maak een masker van de donkere delen (schaduwen) door het beeld te inverteren en te vervagen
    gray = img.convert("L")
    shadow_mask = ImageOps.invert(gray)
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=15)) # Zachte overgangen
    
    # Boost de schaduwen selectief
    boosted_img = Image.eval(img, lambda x: min(255, int(x * shadow_boost)))
    
    # Combineer het origineel met de opgelichte schaduwen op basis van het masker
    hdr_img = Image.composite(boosted_img, img, shadow_mask)
    
    # Voeg een zachte kleurverzadiging toe
    color_enhancer = ImageEnhance.Color(hdr_img)
    hdr_img = color_enhancer.enhance(saturation)
    
    # Subtiel contrast toevoegen zonder dat het zwart dichtloopt
    contrast_enhancer = ImageEnhance.Contrast(hdr_img)
    hdr_img = contrast_enhancer.enhance(1.1)
    
    return hdr_img

def apply_preset(img, preset_name):
    if preset_name == "HDR Natural (Herstel Schaduwen) 🍃":
        # Licht de schaduwen mooi op en maakt kleuren fris maar natuurlijk
        return apply_smart_hdr(img, shadow_boost=1.4, highlight_protect=0.9, saturation=1.2)
        
    elif preset_name == "Golden Hour Sunset 🌅":
        # Warme tinten, lichte schaduwen en diepe gouden gloed
        hdr = apply_smart_hdr(img, shadow_boost=1.3, highlight_protect=0.85, saturation=1.4)
        r, g, b = hdr.split()
        r = r.point(lambda i: min(255, int(i * 1.15))) # Extra rood/oranje warmte
        g = g.point(lambda i: min(255, int(i * 1.04)))
        return Image.merge("RGB", (r, g, b))
        
    elif preset_name == "Cinematic Sky ☁️":
        # Meer dramatiek in de lucht, maar de grond blijft goed zichtbaar
        hdr = apply_smart_hdr(img, shadow_boost=1.5, highlight_protect=0.8, saturation=1.1)
        r, g, b = hdr.split()
        b = b.point(lambda i: min(255, int(i * 1.05))) # Tikje koelere/professionelere look
        return Image.merge("RGB", (r, g, b))
        
    return img # Standaard (geen filter)


# --- WEBSITE INTERFACE ---
uploaded_file = st.file_uploader("Upload je foto...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    original_image = Image.open(uploaded_file)
    
    st.write("---")
    st.subheader("Instellingen")
    
    # Keuzemenu voor presets
    preset = st.selectbox(
        "Kies een Slimme HDR Preset (voorkomt te donkere schaduwen):",
        ["HDR Natural (Herstel Schaduwen) 🍃", "Golden Hour Sunset 🌅", "Cinematic Sky ☁️", "Standaard (Geen filter)"]
    )
    
    auto_level = st.checkbox("Horizon automatisch rechtzetten & croppen", value=True)
    
    # 1. Pas preset toe met schaduw-herstel
    processed_image = apply_preset(original_image, preset)
    
    # 2. Automatische horizon leveler
    if auto_level:
        with st.spinner("Horizon analyseren en rechtzetten..."):
            angle = detect_horizon_angle(original_image)
            # Alleen roteren als de afwijking groter is dan 0.5 graad (voorkomt onnodig kwaliteitsverlies)
            if abs(angle) > 0.5:
                rotated = processed_image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
                processed_image = crop_around_center(rotated, angle)
                st.info(f"Horizon gedetecteerd! Foto is automatisch {angle:.1f}° gecorrigeerd.")
            else:
                st.success("Horizon is al perfect recht!")
                
    # Resultaat tonen
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
                file_name="smart_drone_photo.jpg",
                mime="image/jpeg"
            )
