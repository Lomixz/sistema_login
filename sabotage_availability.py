from app import app, db
from models import User, DisponibilidadProfesor

def sabotaje():
    with app.app_context():
        # Buscar a Roman Gerardo
        # Usamos like por seguridad en el nombre
        p = User.query.filter(User.nombre.like('%Roman%'), User.apellido.like('%Garcia%')).first()
        if p:
            print(f"Saboteando a {p.nombre} {p.apellido} (ID: {p.id})...")
            # Quitar disponibilidad
            DisponibilidadProfesor.query.filter_by(profesor_id=p.id).delete()
            db.session.commit()
            print("😈 Disponibilidad eliminada. Ahora debería fallar la generación con mensaje específico.")
        else:
            print("No encontré a Roman Gerardo.")

if __name__ == '__main__':
    sabotaje()
