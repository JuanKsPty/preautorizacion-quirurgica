"""
Datos de demostracion. Es idempotente: se puede correr las veces que sea.

    pnpm run seed        (o:  uv run --directory api python -m app.seed)

Sirve para arrancar con la base poblada y para repoblarla en un comando despues
de un  pnpm run db:reset.
"""

from sqlmodel import Session, select

from app.core.security import hash_password
from app.db.session import create_db_and_tables, engine
from app.models import Item, User

CORREO_DEMO = "demo@demo.com"
PASSWORD_DEMO = "demo1234"

ITEMS_DEMO = [
    ("Explorar la plantilla", "Revisar las pantallas y los endpoints de ejemplo", True),
    ("Montar el modelo de datos", "Renombrar Item por la entidad real del proyecto", False),
    ("Construir la primera pantalla propia", "Copiar el patron de ItemsPage", False),
]


def main() -> None:
    create_db_and_tables()

    with Session(engine) as session:
        usuario = session.exec(select(User).where(User.email == CORREO_DEMO)).first()

        if usuario is None:
            usuario = User(
                email=CORREO_DEMO,
                full_name="Usuario de demo",
                hashed_password=hash_password(PASSWORD_DEMO),
            )
            session.add(usuario)
            session.commit()
            session.refresh(usuario)
            print(f"Usuario creado: {CORREO_DEMO} / {PASSWORD_DEMO}")
        else:
            print(f"Usuario ya existia: {CORREO_DEMO} / {PASSWORD_DEMO}")

        existentes = {
            item.title
            for item in session.exec(select(Item).where(Item.owner_id == usuario.id)).all()
        }

        creados = 0
        for titulo, descripcion, hecho in ITEMS_DEMO:
            if titulo in existentes:
                continue
            session.add(
                Item(title=titulo, description=descripcion, done=hecho, owner_id=usuario.id)
            )
            creados += 1

        session.commit()
        print(f"Items nuevos: {creados} (ya habia {len(existentes)})")


if __name__ == "__main__":
    main()
