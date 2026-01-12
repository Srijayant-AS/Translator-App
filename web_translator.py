import streamlit as st
import urllib.parse

def main():
    st.title("Link Sharer")

    # The link you want users to copy
    link_to_share = "https://your-awesome-link.com"
    
    st.write("### Step 1: Copy the Link")

    # This is the JavaScript logic for the Copy Button
    copy_button_html = f"""
        <input type="text" value="{link_to_share}" id="myInput" style="width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 5px;" readonly>
        <button onclick="copyFunction()" style="
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            width: 100%;">
            Copy Link
        </button>

        <script>
        function copyFunction() {{
          var copyText = document.getElementById("myInput");
          copyText.select();
          copyText.setSelectionRange(0, 99999); /* For mobile devices */
          navigator.clipboard.writeText(copyText.value);
          alert("Link copied to clipboard!");
        }}
        </script>
    """
    
    # Render the copy button
    st.components.v1.html(copy_button_html, height=130)

    st.divider()

    # 2. Redirect to WhatsApp (Retained exactly as before)
    st.write("### Step 2: Share on WhatsApp")
    
    message = f"Check this out: {link_to_share}"
    encoded_msg = urllib.parse.quote(message)
    whatsapp_url = f"https://wa.me/?text={encoded_msg}"

    st.markdown(
        f"""
        <a href="{whatsapp_url}" target="_blank">
            <button style="
                background-color: #25D366;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                width: 100%;">
                Open WhatsApp to Paste
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()











