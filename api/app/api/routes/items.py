from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, select

from app.core.deps import CurrentUser, SessionDep
from app.models import Item, ItemCreate, ItemPublic, ItemUpdate, User

router = APIRouter(prefix="/items", tags=["items"])


def _buscar_item(item_id: int, usuario: User, session: SessionDep) -> Item:
    """Trae el item solo si pertenece al usuario de la sesion."""
    item = session.get(Item, item_id)
    if item is None or item.owner_id != usuario.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe ese item")
    return item


@router.get("", response_model=list[ItemPublic], summary="Listar mis items")
def listar_items(usuario: CurrentUser, session: SessionDep) -> Sequence[Item]:
    consulta = select(Item).where(Item.owner_id == usuario.id).order_by(col(Item.created_at).desc())
    return session.exec(consulta).all()


@router.post(
    "",
    response_model=ItemPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un item",
)
def crear_item(datos: ItemCreate, usuario: CurrentUser, session: SessionDep) -> Item:
    item = Item(**datos.model_dump(), owner_id=usuario.id)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemPublic, summary="Ver un item")
def ver_item(item_id: int, usuario: CurrentUser, session: SessionDep) -> Item:
    return _buscar_item(item_id, usuario, session)


@router.patch("/{item_id}", response_model=ItemPublic, summary="Actualizar un item")
def actualizar_item(
    item_id: int, datos: ItemUpdate, usuario: CurrentUser, session: SessionDep
) -> Item:
    item = _buscar_item(item_id, usuario, session)

    # exclude_unset: solo tocamos los campos que vinieron en el body.
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(item, campo, valor)

    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Borrar un item")
def borrar_item(item_id: int, usuario: CurrentUser, session: SessionDep) -> None:
    item = _buscar_item(item_id, usuario, session)
    session.delete(item)
    session.commit()
