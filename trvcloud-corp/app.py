from flask import Flask, render_template, request, redirect, url_for
import markdown

app = Flask(__name__)
HANDBOOK_FILE = 'handbook.md'

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/handbook')
def handbook():
    # Read the Markdown file and convert it to HTML
    with open(HANDBOOK_FILE, 'r', encoding='utf-8') as file:
        md_content = file.read()
    handbook_html = markdown.markdown(md_content)
    return render_template('handbook.html', handbook=handbook_html)

@app.route('/edit-handbook', methods=['GET'])
def edit_handbook():
    # Load the current Markdown content into the edit form
    with open(HANDBOOK_FILE, 'r', encoding='utf-8') as file:
        md_content = file.read()
    return render_template('edit_handbook.html', content=md_content)

@app.route('/update-handbook', methods=['POST'])
def update_handbook():
    # Save the updated handbook content from the form
    new_content = request.form.get('handbook_content')
    with open(HANDBOOK_FILE, 'w', encoding='utf-8') as file:
        file.write(new_content)
    return redirect(url_for('handbook'))

@app.route('/chatbot')
def chatbot():
    # Placeholder page for the Chatbot interface
    return render_template('chatbot.html')

if __name__ == '__main__':
    app.run(debug=True)
