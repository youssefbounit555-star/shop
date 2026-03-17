# PythonAnywhere deployment

This project is ready to run on PythonAnywhere as a standard Django WSGI app.

## 1. Recommended Python version

Use Python 3.13 when creating the web app and virtualenv. This project currently uses Django 6.0, which requires Python 3.12 or newer.

## 2. Upload the code

The easiest route is Git:

```bash
git clone https://github.com/<your-user>/<your-repo>.git ~/core
cd ~/core
```

If you upload the files manually, keep `manage.py` at the project root and make sure the folder layout matches this repository.

## 3. Create the virtualenv and install packages

```bash
mkvirtualenv --python=/usr/bin/python3.13 core-venv
cd ~/core
pip install -r requirements.txt
```

If `mkvirtualenv` is not available in your console, create the web app first from the PythonAnywhere Web tab, then create a Bash console and run:

```bash
python3.13 -m venv ~/.virtualenvs/core-venv
source ~/.virtualenvs/core-venv/bin/activate
pip install -r ~/core/requirements.txt
```

## 4. Configure environment variables

Create a `.env` file from the example:

```bash
cd ~/core
cp .env.example .env
nano .env
```

Production values should look like this:

```dotenv
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<strong-random-secret>
DJANGO_ALLOWED_HOSTS=<yourusername>.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<yourusername>.pythonanywhere.com
```

If you use a custom domain, add it to both `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.

Fill the optional keys only if you use them:

- Google/Facebook login
- OpenAI assistant
- Stripe/PayPal payments

## 5. Prepare the database and static files

```bash
cd ~/core
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 6. Create the web app on PythonAnywhere

From the Web tab:

1. Click `Add a new web app`
2. Choose `Manual configuration`
3. Choose `Python 3.13`
4. Set the virtualenv path to `/home/<yourusername>/.virtualenvs/core-venv`

## 7. Configure the WSGI file

Open the generated WSGI file from the Web tab and replace its contents with the template in `deploy/pythonanywhere_wsgi.py.example`, adjusting `<yourusername>` if needed.

## 8. Configure static and media mappings

In the Web tab, add these mappings:

- URL: `/static/` -> Directory: `/home/<yourusername>/core/staticfiles`
- URL: `/media/` -> Directory: `/home/<yourusername>/core/media`

## 9. Reload

Press `Reload` in the Web tab.

## Notes

- The current storefront chat page uses AJAX polling, so the site can run on PythonAnywhere WSGI without needing WebSocket support.
- This repository still contains an ASGI/Channels setup. If you later switch the frontend to true `ws://` or `wss://` sockets, you will need PythonAnywhere ASGI support instead of the normal WSGI setup.
- If Google or Facebook login is enabled, update the callback URLs in their dashboards after deployment.
