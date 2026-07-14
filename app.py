import streamlit as st
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
import math

# Pagina instellingen
st.set_page_config(page_title="Drone & Sunset Photo Editor", page_icon="🛸", layout="centered")

st.title("🛸 Drone & Sunset Photo Editor")
st.write("Geen haperende AI-gokken meer. Jij hebt de volledige controle over de horizon en professionele HDR-presets!")

# Perfecte wiskundige Auto-Crop zonder zwarte randen
def crop_around_center(image, angle):
    if abs(angle) < 0.1:
        return image
        
    w, h = image.size
    angle_rad = math.radians(abs(angle))
    
    # Berekening voor de maximaal haalbare rechthoek binnen de gedraaide foto
    sin_a = math.sin(angle_rad)
    cos_a = math.cos(angle_rad)
    
    if w >= h:
        dest_w = (w * cos_a - h * sin_a) / (cos_a**2 - sin_a**2)
        dest_h = (h * cos_a - w * sin_a) / (cos_a**2 - sin_a**2)
    else:
        dest_w = (h * cos_a - w * sin_a) / (cos_a**2 - sin_a**2)
        dest_h = (w * cos_a - h * sin_a) / (cos_a**2 - sin_a**2)
        
    # Veiligheidsmarge van 95% om er absoluut zeker van te zijn dat alle zwarte randen weg zijn
    dest_w = int(min(w, max(10, dest_w)) * 0.95)
    dest_h = int(min(h, max(10, dest_h)) * 0.95)
    
    left = (w - dest_w) // 2
    top = (h - dest_h) // 2
    right = left + dest_w
    bottom = top + dest_h
    
    return image.crop((left, top, right, bottom))

# Slimme HDR die schaduwen oplicht zonder de foto te verpesten
def apply_smart_hdr(img, shadow_boost=1.35, saturation=1.3):
    img = img.convert("RGB")
    gray = img.convert("L")
    
    # Maak een zacht masker van de donkere delen
    shadow_mask = ImageOps.invert(gray)
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=20))
    
    # Alleen de donkere delen oplichten
    boosted_img = Image.eval(img, lambda x: min(255, int(x * shadow_boost)))
    hdr_img = Image.composite(boosted_img, img, shadow_mask)
    
    # Kleuren boosten
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

# --- INTERFACE ---
uploaded_file = st.file_uploader("Upload je foto...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    original_image = Image.open(uploaded_file)
    
    st.write("---")
    st.subheader("Instellingen")
    
    col_settings_1, col_settings_2 = st.columns(2)
    
    with col_settings_1:
        preset = st.selectbox(
            "Kies een preset style:",
            ["HDR Natural (Herstel Schaduwen) 🍃", "Golden Hour Sunset 🌅", "Cinematic Sky ☁️", "Standaard (Geen filter)"]
        )
        
    with col_settings_2:
        # Staat nu standaard altijd op 0.0 (kaarsrecht). Geen AI-fouten meer!
        angle_input = st.slider(
            "Horizon handmatig rechtzetten (Roteren):",
            min_value=-15.0,
            max_value=15.0,
            value=0.0,
            step=0.5
        )

    # 1. Pas preset toe
    processed_image = apply_preset(original_image, preset)
    
    # 2. Handmatige rotatie + gegarandeerde auto-crop
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
