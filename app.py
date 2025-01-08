from quart import Quart, render_template, request, redirect, url_for
import aiosqlite
import string
import random
import validators

app = Quart(__name__)

async def init_db():
    async with aiosqlite.connect("db.sqlite") as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_link TEXT UNIQUE,
                original_link TEXT,
                clicks INTEGER DEFAULT 0
            )
        """)
        await conn.commit()

async def generate_short_link():
    while True:
        short_link = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        async with aiosqlite.connect("db.sqlite") as conn:
            cursor = await conn.execute("SELECT 1 FROM links WHERE short_link = ?", (short_link,))
            if not await cursor.fetchone():
                return short_link

@app.route("/", methods=["GET", "POST"])
async def index():
    short_link = request.args.get("short_link")
    error = None

    if request.method == "POST":
        form = await request.form
        original_link = form.get("original_link")
        
        if not validators.url(original_link):
            error = "Введите корректный URL."
        else:
            short_link = await generate_short_link()
            
            async with aiosqlite.connect("db.sqlite") as conn:
                await conn.execute("INSERT INTO links (short_link, original_link) VALUES (?, ?)", 
                                   (short_link, original_link))
                await conn.commit()

            return redirect(url_for('index', short_link=short_link))

    return await render_template("index.html", short_link=short_link, error=error)


@app.route("/<short_link>")
async def redirect_to_original(short_link):
    async with aiosqlite.connect("db.sqlite") as conn:
        cursor = await conn.execute("SELECT original_link, clicks FROM links WHERE short_link = ?", 
                                    (short_link,))
        result = await cursor.fetchone()
        
        if result:
            original_link, clicks = result
            await conn.execute("UPDATE links SET clicks = clicks + 1 WHERE short_link = ?", (short_link,))
            await conn.commit()
            return redirect(original_link)
        else:
            return "Ссылка не найдена", 404

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
    app.run(host="0.0.0.0", port=8000, debug=True)
