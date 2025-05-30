from pyngrok import ngrok

# (optional) set your auth token
ngrok.set_auth_token("YOUR_AUTH_TOKEN")

# open an HTTP tunnel on port 8000
public_url = ngrok.connect(8000, "http")
print(" * ngrok tunnel:", public_url)
