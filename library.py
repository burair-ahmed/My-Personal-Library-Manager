import streamlit as st
import json
import os
import base64
from urllib.parse import urlencode
import streamlit.components.v1 as components
import hashlib

# Initialize folders
if not os.path.exists("user_data"):
    os.makedirs("user_data")

# Initialize session state
if 'username' not in st.session_state:
    st.session_state.username = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def get_user_data_path(username):
    user_folder = f"user_data/{username}"
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return f"{user_folder}/library.json"

def get_user_pdf_folder(username):
    pdf_folder = f"user_data/{username}/pdfs"
    if not os.path.exists(pdf_folder):
        os.makedirs(pdf_folder)
    return pdf_folder

def login():
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        # Simple password hashing
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Check if user exists
        if os.path.exists(f"user_data/{username}/credentials.json"):
            with open(f"user_data/{username}/credentials.json", 'r') as f:
                stored_credentials = json.load(f)
                if stored_credentials['password'] == hashed_password:
                    st.session_state.username = username
                    st.session_state.authenticated = True
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid password!")
        else:
            st.error("User does not exist!")

def register():
    username = st.text_input("Choose Username")
    password = st.text_input("Choose Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    
    if st.button("Register"):
        if password != confirm_password:
            st.error("Passwords don't match!")
            return
        
        if os.path.exists(f"user_data/{username}/credentials.json"):
            st.error("Username already exists!")
            return
        
        # Create user directory
        os.makedirs(f"user_data/{username}", exist_ok=True)
        os.makedirs(f"user_data/{username}/pdfs", exist_ok=True)
        
        # Store credentials
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        credentials = {'password': hashed_password}
        with open(f"user_data/{username}/credentials.json", 'w') as f:
            json.dump(credentials, f)
        
        # Initialize empty library
        with open(get_user_data_path(username), 'w') as f:
            json.dump([], f)
            
        st.success("Registration successful! Please login.")

def load_library():
    if not st.session_state.authenticated and not st.query_params.get("shared", False):
        return []
    
    username = st.session_state.username
    if st.query_params.get("shared", False):
        username = st.query_params.get("user", "guest")
    
    data_file = get_user_data_path(username)
    if os.path.exists(data_file):
        with open(data_file, 'r') as file:
            return json.load(file)
    return []

def save_library(library):
    if not st.session_state.authenticated:
        return
    
    data_file = get_user_data_path(st.session_state.username)
    with open(data_file, 'w') as file:
        json.dump(library, file, indent=4)

def show_pdf(pdf_path):
    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        
        # Using a more robust PDF viewer implementation
        pdf_display = f'''
            <embed
                src="data:application/pdf;base64,{base64_pdf}"
                type="application/pdf"
                width="100%"
                height="1200px"
                style="border: none;">
            </embed>
            <script>
                // Ensure PDF is loaded in the viewer
                document.addEventListener('DOMContentLoaded', function() {{
                    var embed = document.querySelector('embed');
                    if (embed.contentDocument && embed.contentDocument.body.innerHTML === "") {{
                        window.location.href = "data:application/pdf;base64,{base64_pdf}";
                    }}
                }});
            </script>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying PDF: {str(e)}")
        # Provide a direct download link as fallback
        st.markdown(f'<a href="data:application/pdf;base64,{base64_pdf}" download="document.pdf">Download PDF</a>', unsafe_allow_html=True)

def add_book(title, author, year, genre, pdf_file):
    library = load_library()
    pdf_path = None
    if pdf_file:
        pdf_folder = get_user_pdf_folder(st.session_state.username)
        pdf_path = os.path.join(pdf_folder, pdf_file.name)
        with open(pdf_path, "wb") as f:
            f.write(pdf_file.getbuffer())
    
    new_book = {
        "title": title,
        "author": author,
        "year": year,
        "genre": genre,
        "pdf_path": pdf_path
    }
    library.append(new_book)
    save_library(library)
    st.success(f"Book '{title}' added successfully!")

def remove_book(title):
    library = load_library()
    updated_library = [book for book in library if book["title"].lower() != title.lower()]
    
    if len(updated_library) < len(library):
        save_library(updated_library)
        st.success(f"Book '{title}' removed successfully!")
    else:
        st.warning(f"Book '{title}' not found in the library.")

def display_books(search_term=None, search_by=None):
    library = load_library()
    if search_term and search_by:
        library = [book for book in library if search_term.lower() in book.get(search_by, "").lower()]
    
    # Check if we're in shared view
    is_shared = st.query_params.get("shared", False)
    
    if library:
        for idx, book in enumerate(library):
            # Create a unique key for this book's state using index
            viewer_key = f"show_pdf_{book['title']}_{idx}"
            if viewer_key not in st.session_state:
                st.session_state[viewer_key] = False

            # Create container for each book
            book_container = st.container()
            with book_container:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"### {book['title']}")
                    st.write(f"by {book['author']} ({book['year']}) - {book['genre']}")
                if book.get("pdf_path"):
                    with col2:
                        with open(book["pdf_path"], "rb") as pdf:
                            st.download_button(
                                label="Download PDF",
                                data=pdf,
                                file_name=os.path.basename(book["pdf_path"]),
                                key=f"download_{book['title']}_{idx}"
                            )
                    # Only show Read Book button if not in shared view
                    if not is_shared:
                        with col3:
                            if st.button(
                                "Read Book" if not st.session_state[viewer_key] else "Close Book",
                                key=f"read_{book['title']}_{idx}"
                            ):
                                st.session_state[viewer_key] = not st.session_state[viewer_key]
                
                if st.session_state[viewer_key]:
                    show_pdf(book["pdf_path"])
                
                st.markdown("---")
    else:
        st.write("No books found in the library.")

def get_shareable_link():
    base_url = "https://mustafayamin-personal-library-manager-library-lohcsi.streamlit.app"
    
    if st.button("Generate Shareable Link"):
        share_link = f"{base_url}?shared=true&user={st.session_state.username}"
        st.code(share_link)
        st.markdown("""
        <div style="margin: 10px 0;">
            <input type="text" value="{}" id="shareLink" 
                   style="width: 100%; padding: 8px; margin-bottom: 5px;" readonly>
            <button onclick="navigator.clipboard.writeText(document.getElementById('shareLink').value)"
                    style="padding: 5px 10px; cursor: pointer;">
                Copy Link
            </button>
        </div>
        """.format(share_link), unsafe_allow_html=True)
        
        st.info("✨ Share this link with others to give them read-only access to your library!")

# Main UI
st.title("📚 Library Manager")

# Get the 'shared' parameter from URL
is_shared = st.query_params.get("shared", False)

if is_shared:
    # Shared view mode
    shared_user = st.query_params.get("user", "guest")
    st.header(f"Shared Library Collection from {shared_user}")
    display_books()
else:
    # Check authentication
    if not st.session_state.authenticated:
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            login()
        with tab2:
            register()
    else:
        # Normal mode with all features
        menu = st.sidebar.selectbox("Menu", ["Add Book", "View Books", "Search Books", "Remove Book", "Share Library"])
        
        # Add logout button
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.rerun()

        if menu == "Add Book":
            st.header("Add a New Book")
            title = st.text_input("Title")
            author = st.text_input("Author")
            year = st.text_input("Year")
            genre = st.text_input("Genre")
            pdf_file = st.file_uploader("Upload Book PDF", type=["pdf"])
            if st.button("Add Book"):
                add_book(title, author, year, genre, pdf_file)

        elif menu == "View Books":
            st.header("Library Collection")
            display_books()

        elif menu == "Search Books":
            st.header("Search Library")
            search_by = st.selectbox("Search by", ["title", "author", "genre", "year"])
            search_term = st.text_input("Enter search term")
            if st.button("Search"):
                display_books(search_term, search_by)

        elif menu == "Remove Book":
            st.header("Remove a Book")
            title = st.text_input("Enter book title to remove")
            if st.button("Remove Book"):
                remove_book(title)

        elif menu == "Share Library":
            st.header("Share Your Library")
            st.write("Generate a shareable link to your library:")
            get_shareable_link()
            st.write("""
            ### Sharing Instructions:
            1. Click the 'Generate Shareable Link' button above
            2. Copy the generated link
            3. Share this link with anyone you want to give access to your library
            4. They will be able to view and read books but cannot modify the library
            """)
