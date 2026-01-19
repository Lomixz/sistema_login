"""
Script de migración para el sistema UPTEX
=========================================

Este script crea las nuevas tablas y migra los datos existentes:
1. Crea la tabla 'role' con los roles predefinidos
2. Crea la tabla 'user_roles' (pivote)
3. Crea la tabla 'asignacion_profesor_grupo'
4. Sincroniza los roles legacy de usuarios existentes

Uso:
    python migrate_roles_grupos.py

Autor: Sistema UPTEX
Fecha: 2026-01-17
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Role, User, AsignacionProfesorGrupo, Grupo, Materia


def create_default_roles():
    """Crear roles predefinidos del sistema"""
    roles_data = [
        ('admin', 'Administrador del sistema con acceso total'),
        ('jefe_carrera', 'Jefe de carrera con acceso a gestión de profesores y materias'),
        ('profesor_completo', 'Profesor de tiempo completo'),
        ('profesor_asignatura', 'Profesor por asignatura/horas'),
    ]
    
    created = 0
    for nombre, descripcion in roles_data:
        existing = Role.query.filter_by(nombre=nombre).first()
        if not existing:
            role = Role(nombre=nombre, descripcion=descripcion)
            db.session.add(role)
            created += 1
            print(f"  ✓ Rol '{nombre}' creado")
        else:
            print(f"  - Rol '{nombre}' ya existe")
    
    db.session.commit()
    return created


def sync_user_roles():
    """Sincronizar roles legacy de usuarios existentes con la nueva tabla many-to-many"""
    users = User.query.all()
    synced = 0
    
    for user in users:
        if user.rol:
            # Verificar si ya tiene el rol en la relación many-to-many
            has_role = any(r.nombre == user.rol for r in user.roles)
            if not has_role:
                role = Role.query.filter_by(nombre=user.rol).first()
                if role:
                    user.roles.append(role)
                    synced += 1
                    print(f"  ✓ Usuario '{user.username}' sincronizado con rol '{user.rol}'")
                else:
                    print(f"  ⚠ Rol '{user.rol}' no encontrado para usuario '{user.username}'")
    
    db.session.commit()
    return synced


def migrate_profesor_materia_to_grupos():
    """
    Migrar las asignaciones existentes profesor-materia a la nueva tabla 
    asignacion_profesor_grupo.
    
    Nota: Como no hay información específica de grupo, se crean asignaciones
    para todos los grupos que tengan la materia.
    """
    # Obtener todas las materias con profesores asignados
    materias_con_profesores = Materia.query.filter(
        Materia.profesores.any()
    ).all()
    
    created = 0
    skipped = 0
    
    for materia in materias_con_profesores:
        # Obtener grupos que tienen esta materia
        grupos_materia = materia.grupos
        
        for profesor in materia.profesores:
            for grupo in grupos_materia:
                # Verificar si ya existe la asignación
                existing = AsignacionProfesorGrupo.query.filter_by(
                    profesor_id=profesor.id,
                    materia_id=materia.id,
                    grupo_id=grupo.id
                ).first()
                
                if not existing:
                    asignacion = AsignacionProfesorGrupo(
                        profesor_id=profesor.id,
                        materia_id=materia.id,
                        grupo_id=grupo.id,
                        horas_semanales=materia.horas_semanales,
                        periodo_academico=f"{2026}-1",
                        notas="Migrado automáticamente desde profesor_materias"
                    )
                    db.session.add(asignacion)
                    created += 1
                    print(f"  ✓ Asignación: {profesor.get_nombre_completo()} -> {materia.nombre} -> {grupo.codigo}")
                else:
                    skipped += 1
    
    db.session.commit()
    return created, skipped


def run_migration():
    """Ejecutar la migración completa"""
    print("\n" + "="*60)
    print("MIGRACIÓN DE SISTEMA UPTEX - Roles y Asignaciones por Grupo")
    print("="*60 + "\n")
    
    with app.app_context():
        # Paso 1: Crear nuevas tablas
        print("Paso 1: Creando nuevas tablas en la base de datos...")
        db.create_all()
        print("  ✓ Tablas creadas exitosamente\n")
        
        # Paso 2: Crear roles predefinidos
        print("Paso 2: Creando roles predefinidos...")
        roles_created = create_default_roles()
        print(f"  Total: {roles_created} roles creados\n")
        
        # Paso 3: Sincronizar usuarios con sus roles
        print("Paso 3: Sincronizando usuarios existentes con la nueva tabla de roles...")
        users_synced = sync_user_roles()
        print(f"  Total: {users_synced} usuarios sincronizados\n")
        
        # Paso 4: Migrar asignaciones profesor-materia a grupos
        print("Paso 4: Migrando asignaciones profesor-materia a grupos específicos...")
        created, skipped = migrate_profesor_materia_to_grupos()
        print(f"  Total: {created} asignaciones creadas, {skipped} ya existían\n")
        
        # Resumen
        print("="*60)
        print("MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print(f"""
Resumen:
  - Roles creados: {roles_created}
  - Usuarios sincronizados: {users_synced}
  - Asignaciones profesor-grupo creadas: {created}
  
Próximos pasos:
  1. Reiniciar la aplicación Flask
  2. Verificar que los usuarios pueden acceder con sus roles
  3. Revisar las asignaciones en la interfaz de administración
""")


if __name__ == '__main__':
    run_migration()
