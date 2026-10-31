# HELPUP - Connect beyond your circle

A mini social network built with **Django**, **HTML5**, **CSS3** and **vanilla JavaScript** (SQLite database). Users can create accounts, build profiles, post text and images, like and comment, follow each other, explore content and discover people **nearby** by city and neighbourhood.

> CodeAlpha Full Stack Development internship project.

## Features
| Area | What it does |
|---|---|
| **Authentication** | Register, log in, log out (Django's built-in auth, hashed passwords, password validation, sessions, protected pages) |
| **Profiles** | Picture, full name, username, bio, city, neighbourhood, interests, joined date; edit your own; followers / following lists |
| **Feed** | Posts from people you follow, a *Latest* tab, and *Recommended for you* when your feed is thin |
| **Posts** | Create / edit / delete your own posts, upload an image with preview, 5 MB and JPG/PNG/GIF/WebP validation |
| **Likes** | AJAX like / unlike with live counts; a user can like a post only once (database constraint) |
| **Comments** | Add and delete (your own) comments inline without a page reload; empty comments are rejected |
| **Follow** | Follow / unfollow buttons (AJAX); no self-follows or duplicates (database constraints) |
| **Explore** | Suggested people, recent posts, search people and posts |
| **Nearby** | Filter by city, neighbourhood and shared interest; people can opt out; **only city and neighbourhood are ever stored or shown, never an address or GPS position** |
| **Notifications** | New follower, post liked, post commented; unread badge in the navigation |
| **Admin** | Users (with inline profile), profiles, posts, comments, likes, follows and notifications with list displays, filters and search |
| **Design** | Responsive (desktop / tablet / mobile tab bar), light and dark mode, Plus Jakarta Sans, palette `#101D29` / `#A3E635` |

Every form also works without JavaScript; the JS layer (`static/js/app.js`) upgrades likes, follows and comments to `fetch` requests that send the CSRF token.

## Run it locally (Windows, macOS, Linux)
Requires **Python 3.10+**.

```bash
# 1. create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 2. install dependencies
pip install -r requirements.txt

# 3. create the database
python manage.py migrate

# 4. (optional) load clearly-labelled DEMO data: 14 people, 42 posts, likes, comments, follows
python manage.py seed_demo

# 5. (optional) create an admin account
python manage.py createsuperuser

# 6. start the server
python manage.py runserver
```
Open **http://127.0.0.1:8000/**. The admin panel is at **/admin/**.

**Demo accounts** (created only by `seed_demo`): `aisha_k`, `bilal_ahmed`, `sana_codes`, `hamza_lens`, `mehr_bakes`, `usman_fit`, `zara_art`, `omar_trails`, `hira_reads`, `danish_dev`, `noor_cafe`, `faisal_fc`, `laiba_plants`, `ali_beats` - password **`helpup123`**.
Run `python manage.py seed_demo --reset` to wipe and recreate only the demo users. No sample data is hardcoded in the templates; everything shown comes from the database.

## Run the tests
```bash
python manage.py test
```
54 tests cover: registration, password validation, login / logout, protected pages, profile editing and avatar upload, creating posts and uploading images (including invalid / oversized files), likes (no duplicates, CSRF), comments (empty rejected, delete own only), follows (no self-follow, no duplicates), explore search, Nearby filters and the opt-out, notifications, and ownership checks (403 when editing or deleting someone else's content).

## Project structure
```
config/          settings, root URLs, 403 handler, test helpers
accounts/        Profile model, register / login / profile views, image validators, seed_demo command
posts/           Post, Comment, Like models; feed, composer, like & comment endpoints
social/          Follow model; follow, followers / following, Explore, Nearby, recommendations
notifications/   Notification model, context processor (unread count), list view
templates/       base layout, partials (post card, user card, avatar...), pages
static/          css/app.css, js/app.js, images/
media/           uploaded images (created at runtime, git-ignored)
```

## Data model
- **Profile** - OneToOne with User (created automatically by a signal); `city`, `neighbourhood`, `interests`, `show_in_nearby`
- **Post** - author, text, image, timestamps
- **Comment** - post, author, text
- **Like** - user, post; `UniqueConstraint(user, post)`
- **Follow** - follower, followee; `UniqueConstraint(follower, followee)` and `CheckConstraint(follower != followee)`
- **Notification** - recipient, actor, verb (follow / like / comment), optional post, `is_read`

## Security notes
- CSRF protection on every POST (forms and `fetch` requests); logout is POST-only
- Django password hashing and validators; session cookies are `HttpOnly` and `SameSite=Lax`
- All pages except the landing page, login and register require authentication
- Ownership checks on edit / delete (403 with a clear message otherwise)
- Uploads are validated by extension, size (5 MB) and Pillow content verification
- Nearby only exposes the city and neighbourhood users typed in, and only for users who opted in
- For production set `DJANGO_DEBUG=0`, a real `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS`, and serve `/media/` through your web server

Built for the CodeAlpha Full Stack Development internship.
