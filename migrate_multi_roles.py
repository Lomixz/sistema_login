"""
Script de migración para sincronizar roles existentes con la tabla user_roles.
Este script:
1. Crea los roles base si no existen
2. Sincroniza el campo legacy 'rol' de cada usuario con la tabla user_roles
"""
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Role

def crear_roles_base():
    """Crear los roles base del sistema si no existen"""
    roles_base = [
        ('admin', 'Administrador del sistema con acceso total'),
        ('jefe_carrera', 'Jefe de Carrera - Gestiona profesores y horarios de su carrera'),
        ('profesor_completo', 'Profesor de Tiempo Completo'),
        ('profesor_asignatura', 'Profesor por Asignatura')
    ]
    
    roles_creados = 0
    for nombre, descripcion in roles_base:
        rol_existente = Role.query.filter_by(nombre=nombre).first()
        if not rol_existente:
            nuevo_rol = Role(nombre=nombre, descripcion=descripcion)
            db.session.add(nuevo_rol)
            roles_creados += 1
            print(f"✅ Rol creado: {nombre}")
        else:
            print(f"ℹ️ Rol ya existe: {nombre}")
    
    if roles_creados > 0:
        db.session.commit()
        print(f"\n{roles_creados} roles base creados.")
    else:
        print("\nTodos los roles base ya existen.")

def sincronizar_roles_usuarios():
    """Sincronizar el campo legacy 'rol' con la tabla user_roles"""
    usuarios = User.query.all()
    usuarios_sincronizados = 0
    
    print(f"\nSincronizando roles para {len(usuarios)} usuarios...")
    
    for usuario in usuarios:
        roles_antes = len(usuario.roles)
        
        # Sincronizar el rol legacy con la tabla user_roles
        if usuario.rol:
            usuario.add_role(usuario.rol)
            
        # Verificar si se agregó algún rol
        if len(usuario.roles) > roles_antes:
            usuarios_sincronizados += 1
            print(f"✅ {usuario.get_nombre_completo()}: {usuario.rol}")
    
    if usuarios_sincronizados > 0:
        db.session.commit()
        print(f"\n{usuarios_sincronizados} usuarios sincronizados con nuevos roles.")
    else:
        print("\nTodos los usuarios ya tienen sus roles sincronizados.")

def mostrar_resumen():
    """Mostrar resumen de roles asignados"""
    print("\n" + "="*60)
    print("RESUMEN DE ROLES EN EL SISTEMA")
    print("="*60)
    
    roles = Role.query.all()
    for rol in roles:
        usuarios_con_rol = rol.users.count()
        print(f"\n📌 {rol.get_display_name()} ({rol.nombre})")
        print(f"   Usuarios: {usuarios_con_rol}")
        
        # Mostrar usuarios con múltiples roles
        if usuarios_con_rol <= 10:
            for usuario in rol.users:
                otros_roles = [r.nombre for r in usuario.roles if r.nombre != rol.nombre]
                if otros_roles:
                    print(f"   - {usuario.get_nombre_completo()} (+ {', '.join(otros_roles)})")
                else:
                    print(f"   - {usuario.get_nombre_completo()}")
    
    # Usuarios con múltiples roles
    print("\n" + "="*60)
    print("USUARIOS CON MÚLTIPLES ROLES")
    print("="*60)
    
    usuarios = User.query.all()
    usuarios_multirrol = [u for u in usuarios if len(u.roles) > 1]
    
    if usuarios_multirrol:
        for usuario in usuarios_multirrol:
            roles_nombres = [r.get_display_name() for r in usuario.roles]
            print(f"\n👤 {usuario.get_nombre_completo()}")
            print(f"   Roles: {', '.join(roles_nombres)}")
    else:
        print("\nNo hay usuarios con múltiples roles aún.")

if __name__ == '__main__':
    with app.app_context():
        print("="*60)
        print("MIGRACIÓN DE ROLES - Sistema de Roles Múltiples")
        print("="*60)
        
        # Paso 1: Crear roles base
        print("\n📋 PASO 1: Creando roles base...")
        crear_roles_base()
        
        # Paso 2: Sincronizar roles de usuarios
        print("\n📋 PASO 2: Sincronizando roles de usuarios...")
        sincronizar_roles_usuarios()
        
        # Paso 3: Mostrar resumen
        mostrar_resumen()
        
        print("\n" + "="*60)
        print("✅ MIGRACIÓN COMPLETADA")
        print("="*60)
