# 🔴 PROBLEMA CRÍTICO - Backend No Envía Notificaciones Push

## ✅ Confirmado - Lo que SÍ funciona:
- ✅ Tokens FCM se registran correctamente en `ppavac_dispositivo`
- ✅ Cuando se envía notificación manualmente desde Firebase Console, **SÍ llega al dispositivo**
- ✅ El token FCM es válido y funcional
- ✅ Frontend está configurado correctamente
- ✅ Badge de pendientes funciona (el endpoint de conteo funciona)

## ❌ PROBLEMA CONFIRMADO:
**El backend NO está enviando notificaciones automáticamente cuando se crea una solicitud de vacaciones o permiso.**

---

## 🔍 Qué Revisar en el Backend

### 1. Verificar que se Llame la Función de Envío

**Ubicación:** Endpoint `POST /api/v1/vacaciones/solicitar` y `POST /api/v1/permisos/solicitar`

**Problema:** Después de insertar la solicitud en `ppavac_solicitud`, **NO se está llamando** a la función que envía notificaciones push.

**Qué buscar en el código:**
```python
# Después de crear la solicitud (INSERT en ppavac_solicitud)
# DEBE haber código como esto:

# Obtener datos de la solicitud creada
id_solicitud = resultado_insert.id_solicitud  # o como se obtenga el ID
codigo_trabajador_solicitante = body.codigo_trabajador
tipo_solicitud = 'V'  # 'V' para vacaciones, 'P' para permisos

# ⚠️ ESTA LLAMADA DEBE EXISTIR:
enviar_notificacion_nueva_solicitud(
    id_solicitud=id_solicitud,
    tipo_solicitud=tipo_solicitud,
    codigo_trabajador_solicitante=codigo_trabajador_solicitante
)
```

**Verificar:**
- [ ] ¿Existe esta función `enviar_notificacion_nueva_solicitud` o similar?
- [ ] ¿Se está llamando después de crear la solicitud?
- [ ] ¿Hay algún `try-except` que esté silenciando errores?

---

### 2. Verificar la Función de Envío de Notificaciones

**La función debe hacer lo siguiente:**

#### Paso 1: Identificar Aprobadores
```sql
-- Obtener aprobadores según la jerarquía del trabajador solicitante
SELECT DISTINCT 
    j.codigo_trabajador_aprobador,
    j.nivel
FROM ppavac_jerarquia j
INNER JOIN trabajadores t ON t.codigo_area = j.codigo_area
WHERE t.codigo_trabajador = @codigo_trabajador_solicitante
  AND j.activo = 'S'
ORDER BY j.nivel ASC
```

**Importante:** Solo debe obtener aprobadores del nivel más bajo primero (según la lógica de aprobación jerárquica).

#### Paso 2: Obtener Tokens FCM de los Aprobadores
```sql
-- Obtener tokens FCM de los aprobadores identificados
SELECT 
    token_fcm,
    codigo_trabajador
FROM ppavac_dispositivo
WHERE codigo_trabajador IN (@lista_codigos_aprobadores)
  AND activo = 'S'
  AND (notif_nuevas = 'S' OR notif_nuevas IS NULL)
  AND token_fcm IS NOT NULL
  AND token_fcm != ''
```

#### Paso 3: Enviar Notificaciones con Firebase Admin SDK
```python
from firebase_admin import messaging

# Para cada token FCM obtenido:
message = messaging.Message(
    notification=messaging.Notification(
        title="Nueva Solicitud de Vacaciones" if tipo_solicitud == 'V' else "Nueva Solicitud de Permiso",
        body=f"El trabajador {nombre_trabajador} ha creado una nueva solicitud"
    ),
    data={
        "tipo_solicitud": tipo_solicitud,  # 'V' o 'P'
        "id_solicitud": str(id_solicitud),
        "codigo_trabajador": codigo_trabajador_solicitante,
        "tipo": "nueva_solicitud"  # Para identificar el tipo de notificación
    },
    token=token_fcm,
    android=messaging.AndroidConfig(
        priority='high',
        notification=messaging.AndroidNotification(
            channel_id='fidesoft_channel',  # ⚠️ IMPORTANTE: Este canal debe coincidir
            sound='default',
            click_action='FLUTTER_NOTIFICATION_CLICK'
        )
    )
)

try:
    response = messaging.send(message)
    print(f"Notificación enviada exitosamente: {response}")
except Exception as e:
    print(f"Error al enviar notificación: {e}")
    # NO silenciar el error, registrarlo en logs
```

---

### 3. Verificar Logs del Backend

**Cuando se crea una solicitud, los logs deben mostrar:**

```
[INFO] Solicitud creada: ID=123, Trabajador=PR014793, Tipo=V
[INFO] Identificando aprobadores para trabajador: PR014793
[INFO] Aprobadores encontrados: ['APR001', 'APR002']
[INFO] Obteniendo tokens FCM para aprobadores...
[INFO] Tokens FCM obtenidos: 2 tokens
[INFO] Enviando notificaciones push...
[INFO] Notificación enviada a APR001: success
[INFO] Notificación enviada a APR002: success
```

**Si NO ves estos logs:**
- La función no se está llamando
- O hay un `try-except` que está silenciando los logs

---

### 4. Verificar Inicialización de Firebase Admin SDK

**El backend debe tener:**

```python
import firebase_admin
from firebase_admin import credentials, messaging

# Inicializar Firebase Admin (solo una vez al inicio de la app)
if not firebase_admin._apps:
    cred = credentials.Certificate("path/to/serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK inicializado correctamente")
```

**Verificar:**
- [ ] ¿Firebase Admin SDK está inicializado?
- [ ] ¿El archivo `serviceAccountKey.json` existe y es válido?
- [ ] ¿Las credenciales son del mismo proyecto Firebase que el `google-services.json` del frontend?

---

### 5. Verificar Endpoints de Permisos

**El mismo problema puede existir en:**
- `POST /api/v1/permisos/solicitar`

**Verificar que también envíe notificaciones cuando se crea un permiso.**

---

## 🛠️ Solución Esperada

### Código que DEBE existir en el endpoint de crear solicitud:

```python
@router.post("/vacaciones/solicitar")
async def crear_solicitud_vacaciones(body: SolicitudVacacionesBody):
    # ... código existente para crear la solicitud ...
    
    # Después de insertar en ppavac_solicitud
    id_solicitud = resultado_insert.id_solicitud
    codigo_trabajador = body.codigo_trabajador
    
    # ⚠️ AGREGAR ESTA LLAMADA:
    try:
        await enviar_notificacion_nueva_solicitud(
            id_solicitud=id_solicitud,
            tipo_solicitud='V',
            codigo_trabajador_solicitante=codigo_trabajador
        )
    except Exception as e:
        # Registrar error pero NO fallar la creación de la solicitud
        logger.error(f"Error al enviar notificaciones: {e}")
    
    return {"success": True, "id_solicitud": id_solicitud}
```

---

## 📋 Checklist para el Backend

- [ ] ¿Existe la función `enviar_notificacion_nueva_solicitud` o similar?
- [ ] ¿Se llama después de crear solicitud de vacaciones?
- [ ] ¿Se llama después de crear solicitud de permisos?
- [ ] ¿La función identifica correctamente los aprobadores según la jerarquía?
- [ ] ¿La función obtiene los tokens FCM de `ppavac_dispositivo`?
- [ ] ¿Firebase Admin SDK está inicializado correctamente?
- [ ] ¿Los logs muestran intentos de envío de notificaciones?
- [ ] ¿El `channel_id` en el mensaje es `'fidesoft_channel'`?
- [ ] ¿Los errores se están registrando en logs (no silenciados)?

---

## 🧪 Prueba Rápida

**Crear un endpoint de prueba para verificar que el envío funciona:**

```python
@router.post("/notificaciones/test-envio")
async def test_envio_notificacion(token_fcm: str):
    """
    Endpoint de prueba para verificar que el envío de notificaciones funciona.
    Usar con el token_fcm del aprobador desde la base de datos.
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="Prueba de Notificación",
                body="Esta es una notificación de prueba desde el backend"
            ),
            data={
                "tipo_solicitud": "V",
                "id_solicitud": "999",
                "tipo": "test"
            },
            token=token_fcm,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id='fidesoft_channel'
                )
            )
        )
        
        response = messaging.send(message)
        return {
            "success": True, 
            "message": "Notificación enviada exitosamente",
            "message_id": response
        }
    except Exception as e:
        return {
            "success": False, 
            "error": str(e)
        }
```

**Si este endpoint funciona pero las notificaciones automáticas no, el problema está en que la función no se está llamando cuando se crea la solicitud.**

---

## 📝 Resumen del Problema

1. **Frontend funciona correctamente** ✅
2. **Tokens FCM son válidos** ✅ (confirmado con prueba manual desde Firebase Console)
3. **Backend NO envía notificaciones automáticamente** ❌
4. **Solución:** Agregar llamada a función de envío después de crear solicitud

---

## 🎯 Acción Requerida

**Revisar y corregir:**
1. Endpoint `POST /api/v1/vacaciones/solicitar` - Agregar envío de notificaciones
2. Endpoint `POST /api/v1/permisos/solicitar` - Agregar envío de notificaciones
3. Verificar que la función de envío existe y funciona correctamente
4. Agregar logs para debugging
5. Verificar que Firebase Admin SDK esté inicializado
