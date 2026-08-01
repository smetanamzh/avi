import logging

from sqlalchemy import select

from app.database.database import SessionLocal, engine, Base
from app.database.models import Post

logger = logging.getLogger("basket")


class Repository:

    def __init__(self):
        self.session = SessionLocal()

    def reset_db(self):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.session.commit()
        logger.info("БД сброшена")

    def add_post(
        self,
        source: str,
        external_id: str,
        text: str,
    ):
        exists = self.session.scalar(
            select(Post).where(
                Post.source == source,
                Post.external_id == str(external_id),
            )
        )

        if exists:
            return

        post = Post(
            source=source,
            external_id=str(external_id),
            text=text,
        )

        self.session.add(post)
        self.session.commit()

    def get_unprocessed_posts(self, limit: int = 0):
        stmt = select(Post).where(Post.processed == False).order_by(Post.id)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt))

    def get_ready_posts(self):
        return list(
            self.session.scalars(
                select(Post).where(
                    Post.processed == True,
                    Post.published == False,
                    Post.rewritten_text.is_not(None),
                )
            )
        )

    def get_all_rewritten_texts(self):
        rows = self.session.execute(
            select(Post.rewritten_text).where(
                Post.rewritten_text.is_not(None),
            )
        )
        return [row[0] for row in rows]

    def save_analysis(
        self,
        post: Post,
        rewritten: str,
        category: str,
        importance: int,
    ):
        post.rewritten_text = rewritten
        post.category = category
        post.importance = importance
        post.processed = True
        self.session.commit()

    def reset_analysis(self):
        posts = list(
            self.session.scalars(
                select(Post).where(
                    Post.processed == True,
                    Post.published == False,
                    Post.rewritten_text.is_not(None),
                )
            )
        )
        for post in posts:
            post.processed = False
            post.rewritten_text = None
            post.category = None
            post.importance = None
        self.session.commit()
        if posts:
            logger.info(f"Сброшено {len(posts)} старых анализов")

    def mark_duplicate(self, post: Post):
        post.processed = True
        post.published = True
        self.session.commit()

    def mark_skipped(self, post: Post):
        post.processed = True
        self.session.commit()

    def mark_published(self, post: Post):
        post.published = True
        self.session.commit()
