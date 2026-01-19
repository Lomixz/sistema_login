"""
Script de diagnóstico detallado para identificar EXACTAMENTE por qué falla la generación.
Analiza conflictos de profesores compartidos entre grupos.
"""

from app import app, db
from models import (Grupo, AsignacionProfesorGrupo, DisponibilidadProfesor, 
                    Materia, Horario, User)
from collections import defaultdict

def diagnostico_detallado():
    with app.app_context():
        print("="*80)
        print("🔬 DIAGNÓSTICO DETALLADO DE CONFLICTOS")
        print("="*80)
        
        grupos = Grupo.query.filter_by(activo=True).all()
        grupos_matutino = [g for g in grupos if g.turno == 'M']
        
        print(f"\n📌 Analizando {len(grupos_matutino)} grupos MATUTINOS")
        
        # 1. Identificar profesores compartidos y sus cargas
        print("\n" + "-"*80)
        print("👨‍🏫 ANÁLISIS DE CARGA POR PROFESOR")
        print("-"*80)
        
        profesor_carga = defaultdict(lambda: {'grupos': set(), 'horas': 0, 'materias': []})
        
        for grupo in grupos_matutino:
            materias = [m for m in grupo.materias if m.activa]
            
            for materia in materias:
                # Buscar asignación
                asigs = AsignacionProfesorGrupo.query.filter_by(
                    grupo_id=grupo.id,
                    materia_id=materia.id,
                    activo=True
                ).all()
                
                if asigs:
                    # Usar solo el primero (el que usaría el generador mejorado)
                    asig = asigs[0]
                    if asig.profesor:
                        pid = asig.profesor_id
                        nombre = f"{asig.profesor.nombre} {asig.profesor.apellido}"
                        horas = materia.horas_semanales or 3
                        
                        profesor_carga[pid]['nombre'] = nombre
                        profesor_carga[pid]['grupos'].add(grupo.codigo)
                        profesor_carga[pid]['horas'] += horas
                        profesor_carga[pid]['materias'].append(f"{grupo.codigo}: {materia.nombre} ({horas}h)")
                else:
                    # Fallback a M2M
                    profesores = [p for p in materia.profesores if p.activo]
                    if profesores:
                        profesor = profesores[0]  # El generador tomaría uno
                        pid = profesor.id
                        nombre = f"{profesor.nombre} {profesor.apellido}"
                        horas = materia.horas_semanales or 3
                        
                        profesor_carga[pid]['nombre'] = nombre
                        profesor_carga[pid]['grupos'].add(grupo.codigo)
                        profesor_carga[pid]['horas'] += horas
                        profesor_carga[pid]['materias'].append(f"{grupo.codigo}: {materia.nombre} ({horas}h)")
        
        # Mostrar profesores con más carga
        profesores_ordenados = sorted(profesor_carga.items(), key=lambda x: x[1]['horas'], reverse=True)
        
        conflictos_detectados = []
        
        for pid, data in profesores_ordenados:
            # Obtener disponibilidad en turno matutino
            horarios_mat = Horario.query.filter_by(turno='matutino', activo=True).all()
            dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
            
            slots_disponibles = 0
            for horario in horarios_mat:
                for dia in dias:
                    disp = DisponibilidadProfesor.query.filter_by(
                        profesor_id=pid,
                        horario_id=horario.id,
                        dia_semana=dia,
                        activo=True,
                        disponible=True
                    ).first()
                    if disp:
                        slots_disponibles += 1
            
            # Verificar si es conflicto
            es_conflicto = data['horas'] > slots_disponibles
            es_advertencia = len(data['grupos']) > 1 and data['horas'] > slots_disponibles * 0.8
            
            print(f"\n{'❌' if es_conflicto else '⚠️' if es_advertencia else '✅'} {data['nombre']}")
            print(f"   Horas requeridas: {data['horas']}")
            print(f"   Slots disponibles (matutino): {slots_disponibles}")
            print(f"   Grupos: {', '.join(data['grupos'])}")
            
            if es_conflicto:
                conflictos_detectados.append({
                    'profesor': data['nombre'],
                    'horas_requeridas': data['horas'],
                    'slots_disponibles': slots_disponibles,
                    'deficit': data['horas'] - slots_disponibles,
                    'grupos': data['grupos'],
                    'materias': data['materias']
                })
        
        # 2. Análisis de conflictos por hora/día específico
        print("\n" + "-"*80)
        print("⏰ ANÁLISIS DE CONFLICTOS POR SLOT HORARIO")
        print("-"*80)
        
        horarios_mat = Horario.query.filter_by(turno='matutino', activo=True).order_by(Horario.orden).all()
        dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes']
        
        conflictos_slot = []
        
        for horario in horarios_mat:
            for dia in dias:
                # ¿Cuántos grupos necesitan este slot?
                grupos_necesitan = len(grupos_matutino)
                
                # ¿Cuántos profesores (únicos) están disponibles?
                profesores_disponibles = set()
                for pid in profesor_carga.keys():
                    disp = DisponibilidadProfesor.query.filter_by(
                        profesor_id=pid,
                        horario_id=horario.id,
                        dia_semana=dia,
                        activo=True,
                        disponible=True
                    ).first()
                    if disp:
                        profesores_disponibles.add(pid)
                
                # Verificar déficit
                if len(profesores_disponibles) < grupos_necesitan:
                    conflictos_slot.append({
                        'horario': f"{horario.get_hora_inicio_str()}-{horario.get_hora_fin_str()}",
                        'dia': dia,
                        'grupos_necesitan': grupos_necesitan,
                        'profesores_disponibles': len(profesores_disponibles),
                        'deficit': grupos_necesitan - len(profesores_disponibles)
                    })
        
        if conflictos_slot:
            # Ordenar por déficit
            conflictos_slot.sort(key=lambda x: x['deficit'], reverse=True)
            print("\nSlots con déficit de profesores:")
            for c in conflictos_slot[:10]:
                print(f"   ❌ {c['dia'].capitalize()} {c['horario']}: "
                      f"Necesitan {c['grupos_necesitan']} grupos, "
                      f"disponibles {c['profesores_disponibles']} profesores "
                      f"(déficit: {c['deficit']})")
        else:
            print("\n✅ No hay déficit de profesores por slot")
        
        # 3. RESUMEN Y SOLUCIONES
        print("\n" + "="*80)
        print("📋 RESUMEN Y SOLUCIONES")
        print("="*80)
        
        if conflictos_detectados:
            print("\n❌ CONFLICTOS DE CARGA DE PROFESORES:")
            for c in conflictos_detectados:
                print(f"\n   Profesor: {c['profesor']}")
                print(f"   Déficit: {c['deficit']} horas")
                print(f"   Grupos afectados: {', '.join(c['grupos'])}")
                print("   Soluciones posibles:")
                print("     1. Aumentar disponibilidad del profesor")
                print("     2. Reasignar algunas materias a otros profesores")
                print("     3. Generar grupos por separado (uno a la vez)")
        
        # 4. RECOMENDACIÓN FINAL
        print("\n" + "="*80)
        print("💡 RECOMENDACIÓN")
        print("="*80)
        
        # Agrupar grupos que NO comparten profesores
        grupos_independientes = []
        grupos_procesados = set()
        
        for grupo in grupos_matutino:
            if grupo.id in grupos_procesados:
                continue
            
            grupo_actual = {grupo.id}
            grupos_procesados.add(grupo.id)
            
            # Encontrar profesores de este grupo
            profesores_grupo = set()
            asigs = AsignacionProfesorGrupo.query.filter_by(grupo_id=grupo.id, activo=True).all()
            for asig in asigs:
                if asig.profesor_id:
                    profesores_grupo.add(asig.profesor_id)
            
            grupos_independientes.append({
                'grupos': [grupo.codigo],
                'ids': [grupo.id],
                'profesores': profesores_grupo
            })
        
        print("\nPuedes intentar generar los siguientes grupos de forma INDIVIDUAL:")
        for i, grupo in enumerate(grupos_matutino, 1):
            print(f"   {i}. {grupo.codigo} (ID: {grupo.id})")
        
        print("\n💡 COMANDO RECOMENDADO:")
        print("   Genera grupo por grupo usando la función de generación individual")
        print("   O usa el siguiente código:")
        print("""
from generador_horarios import generar_horarios_automaticos

# Generar uno por uno
for grupo_id in [1, 7, 8, 11, 12, 14, 15]:
    resultado = generar_horarios_automaticos(
        grupo_id=grupo_id,
        periodo_academico='2026-1',
        version_nombre='Individual'
    )
    print(f"Grupo {grupo_id}: {resultado['mensaje']}")
""")

if __name__ == '__main__':
    diagnostico_detallado()
