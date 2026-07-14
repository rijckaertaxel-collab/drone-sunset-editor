import streamlit as st
from PIL import Image, ImageEnhance
import numpy as np
import math

# Pagina instellingen
st.set_page_config(page_title="Drone & Sunset Photo Editor", page_icon="🛸", layout="centered")

st.title("🛸 Advanced Drone Photo Editor")
st.write("Zet je horizon recht, crop automatisch en kies professionele presets!")

# HULPFUNCTIE: Automatisch bijsnijden na rotatie om zwarte randen te voorkomen
def crop_around_center(image, angle):
    """
    Snijdt de zwarte randen weg die ontstaan na het roteren van een afbeelding.
    """
    if angle == 0:
        return image
        
    w, h = image.size
    angle_rad = math.radians(abs(angle))
    
    # Bereken de maximale grootte van de binnenste rechthoek zonder zwarte randen
    if w <= h:
        sin_a = math.sin(angle_rad)
        cos_a = math.cos(angle_rad)
        alpha = min(angle_rad, math.pi / 2 - angle_rad)
        
        dest_w = w * cos_a - h * sin_a
        dest_h = h * cos_a - w * sin_a
    else:
        # Wissel breedte en hoogte om voor landscape foto's
        sin_a = math.sin(angle_rad)
        cos_a = math.cos(angle_rad)
        dest_w = w / (cos_a + sin_a * (w / h))
        dest_h = dest_w * (h / w)
        
    # Zorg dat we niet negatief gaan of buiten de grenzen vallen
    dest_w = max(10, min(w, int(dest_w)))
    dest_h = max(10, min(h, int(dest_h)))
    
    # Snijd het centrum uit
    left = (w - dest_w) // 2
    top = (h - dest_h) // 2
    right = left + dest_w
    bottom = top + dest_h
    
    return image.crop((left, top, right, bottom))

# Filter / Preset Toepassen
def apply_preset(img, preset_name):
    img = img.convert("RGB")
    
    if preset_name == "Golden Hour Boost 🌅":
        # Warm, zonsondergang-effect
        img = ImageEnhance.Color(img).enhance(1.6)
        img = ImageEnhance.Contrast(img).enhance(1.25)
        r, g, b = img.split()
        r = r.point(lambda i: min(255, int(i * 1.18)))
        g = g.point(lambda i: min(255, int(i * 1.05)))
        return Image.merge("RGB", (r, g, b))
        
    elif preset_name == "Cinematic Drone 🎬":
        # Filmische look: iets minder verzadiging, intenser contrast, diepe schaduwen
        img = ImageEnhance.Contrast(img).enhance(1.4)
        img = ImageEnhance.Color(img).enhance(1.1)
        r, g, b = img.split()
        b = b.point(lambda i: min(255, int(i * 1.08))) # Tikje blauwer in de schaduwen
        return Image.merge("RGB", (r, g, b))
        
    elif preset_name == "Vibrant Nature 🌲":
        # Felle kleuren voor bossen, zee, bergen
        img = ImageEnhance.Color(img).enhance(1.75)
        img = ImageEnhance.Contrast(img).enhance(1.2)
        img = ImageEnhance.Brightness(img).enhance(1.05)
        return img
        
    # "Standaard" geeft gewoon de originele kleuren terug
    return img

# --- WEBSITE INTERFACE ---

uploaded_file = st.file_uploader("Kies een drone- of landschapsfoto...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Laad de originele afbeelding
    original_image = Image.open(uploaded_file)
    
    # Instellingen menu in de sidebar (of bovenin)
    st.write("---")
    st.subheader("Bewerken & Presets")
    
    col_settings_1, col_settings_2 = st.columns(2)
    
    with col_settings_1:
        # 1. Preset kiezen
        preset = st.selectbox(
            "Kies een AI Preset Style:",
            ["Standaard (Geen filter)", "Golden Hour Boost 🌅", "Cinematic Drone 🎬", "Vibrant Nature 🌲"]
        )
        
    with col_settings_2:
        # 2. Horizon Leveler
        rotation_angle = st.slider(
            "Horizon rechtzetten (Roteren):",
            min_value=-15.0,
            max_value=15.0,
            value=0.0,
            step=0.1,
            help="Sleep om de foto te roteren. De app snijdt de foto automatisch bij om zwarte randen te verwijderen!"
        )
        
    # Beeldbewerking uitvoeren
    # Eerst de preset toepassen
    processed_image = apply_preset(original_image, preset)
    
    # Daarna roteren en automatisch croppen (als er rotatie is)
    if rotation_angle != 0.0:
        # We roteren met expand=False zodat de foto op dezelfde resolutie blijft, 
        # waarna we de zwarte randen weg-croppen
        rotated = processed_image.rotate(rotation_angle, resample=Image.BICUBIC, expand=False)
        processed_image = crop_around_center(rotated, rotation_angle)

    # Resultaat tonen
    st.write("---")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Origineel")
        st.image(original_image, use_container_width=True)
        
    with col2:
        st.subheader("Resultaat ✨")
        st.image(processed_image, use_container_width=True)
        
        # Tijdelijk opslaan voor de downloadknop
        processed_image.save("edited_output.jpg", "JPEG", quality=95)
        with open("edited_output.jpg", "rb") as file:
            st.download_button(
                label="Download Bewerkte Foto 📥",
                data=file,
                file_name="drone_edited.jpg",
                mime="image/jpeg"
            )
