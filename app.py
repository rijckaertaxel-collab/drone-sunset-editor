import streamlit as st
from PIL import Image, ImageEnhance

# Pagina instellingen
st.set_page_config(page_title="Drone & Sunset Photo Editor", page_icon="🛸", layout="centered")

st.title("🛸 Drone & Sunset Photo Editor")
st.write("Upload je foto en laat de filters de kleuren en het contrast automatisch optimaliseren!")

# Upload knop
uploaded_file = st.file_uploader("Kies een drone- of sunsetfoto...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Open de afbeelding
    image = Image.open(uploaded_file)
    
    # Maak twee kolommen naast elkaar
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Origineel")
        st.image(image, use_container_width=True)
        
    # Foto bewerken
    img = image.convert("RGB")
    
    # 1. Kleurverzadiging boosten
    converter = ImageEnhance.Color(img)
    img = converter.enhance(1.6)
    
    # 2. Contrast boosten
    contrast = ImageEnhance.Contrast(img)
    img = contrast.enhance(1.25)
    
    # 3. Warme gloed (sunset filter)
    r, g, b = img.split()
    r = r.point(lambda i: min(255, int(i * 1.18)))
    g = g.point(lambda i: min(255, int(i * 1.05)))
    
    edited_image = Image.merge("RGB", (r, g, b))
    
    with col2:
        st.subheader("Bewerkt ✨")
        st.image(edited_image, use_container_width=True)
        
        # Download knop voor de bewerkte foto
        # We slaan de foto tijdelijk op om te kunnen downloaden
        edited_image.save("edited.jpg", "JPEG")
        with open("edited.jpg", "rb") as file:
            st.download_button(
                label="Download Bewerkte Foto 📥",
                data=file,
                file_name="sunset_boosted.jpg",
                mime="image/jpeg"
            )
