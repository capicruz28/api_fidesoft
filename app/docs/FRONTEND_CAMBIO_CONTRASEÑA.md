# 📋 Documentación Frontend - Cambio de Contraseña

## 🔗 Endpoint

**URL:** `POST /api/v1/auth/change-password/`

**URL Completa:** `https://tu-dominio.com/api/v1/auth/change-password/`

---

## 🔐 Autenticación

Este endpoint requiere autenticación mediante **Access Token JWT**.

### Headers Requeridos

```http
Authorization: Bearer <tu_access_token>
Content-Type: application/json
```

**Ejemplo:**
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

---

## 📤 Request Body

### Estructura JSON

```json
{
  "contrasena_actual": "string",
  "nueva_contrasena": "string"
}
```

### Campos

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `contrasena_actual` | string | ✅ Sí | Contraseña actual del usuario |
| `nueva_contrasena` | string | ✅ Sí | Nueva contraseña que reemplazará la actual |

### Validaciones del Cliente (Frontend)

Antes de enviar la petición, valida en el frontend:

1. **Contraseña actual:**
   - ✅ No puede estar vacía
   - ✅ Mínimo 1 carácter

2. **Nueva contraseña:**
   - ✅ Mínimo 8 caracteres
   - ✅ Al menos una letra mayúscula (A-Z)
   - ✅ Al menos una letra minúscula (a-z)
   - ✅ Al menos un número (0-9)
   - ✅ Debe ser diferente a la contraseña actual

---

## 📥 Respuestas

### ✅ 200 OK - Contraseña Cambiada Exitosamente

**Respuesta para Usuario Local:**
```json
{
  "message": "Contraseña cambiada exitosamente",
  "usuario_id": 123,
  "nombre_usuario": "juan.perez",
  "origen_datos": "local"
}
```

**Respuesta para Usuario Cliente:**
```json
{
  "message": "Contraseña cambiada exitosamente en sistema cliente",
  "usuario_id": 456,
  "nombre_usuario": "44010473",
  "origen_datos": "cliente"
}
```

---

### ❌ 400 Bad Request - Contraseña Actual Incorrecta

```json
{
  "detail": "La contraseña actual es incorrecta",
  "error_code": "INVALID_CURRENT_PASSWORD"
}
```

**Cuándo ocurre:**
- La contraseña actual proporcionada no coincide con la contraseña almacenada

**Acción del frontend:**
- Mostrar mensaje de error al usuario
- Resaltar el campo de contraseña actual
- Permitir reintentar

---

### ❌ 400 Bad Request - Contraseñas Iguales

```json
{
  "detail": "La nueva contraseña debe ser diferente a la contraseña actual"
}
```

**Cuándo ocurre:**
- La nueva contraseña es igual a la contraseña actual

**Acción del frontend:**
- Mostrar mensaje de error
- Sugerir usar una contraseña diferente

---

### ❌ 401 Unauthorized - Token Inválido o Expirado

```json
{
  "detail": "No se pudieron validar las credenciales"
}
```

**Cuándo ocurre:**
- El Access Token no está presente en el header
- El Access Token es inválido
- El Access Token ha expirado

**Acción del frontend:**
- Redirigir al usuario al login
- Limpiar tokens almacenados
- Intentar refrescar el token si está disponible

---

### ❌ 422 Unprocessable Entity - Validación de Nueva Contraseña

```json
{
  "detail": "La contraseña no cumple con los requisitos de seguridad. Debe contener: al menos una letra mayúscula, al menos un número."
}
```

**Cuándo ocurre:**
- La nueva contraseña no cumple con los requisitos de seguridad

**Acción del frontend:**
- Mostrar mensaje de error específico
- Resaltar qué requisitos faltan
- Mostrar indicadores visuales de cumplimiento de requisitos

---

### ❌ 500 Internal Server Error

```json
{
  "detail": "Error interno del servidor al cambiar la contraseña.",
  "error_code": "INTERNAL_ERROR"
}
```

**Cuándo ocurre:**
- Error inesperado en el servidor

**Acción del frontend:**
- Mostrar mensaje genérico de error
- Sugerir intentar más tarde
- Registrar el error para debugging

---

## 💻 Ejemplos de Implementación

### 🌐 JavaScript/TypeScript (Fetch API)

```typescript
interface ChangePasswordRequest {
  contrasena_actual: string;
  nueva_contrasena: string;
}

interface ChangePasswordResponse {
  message: string;
  usuario_id: number;
  nombre_usuario: string;
  origen_datos: string;
}

async function cambiarContrasena(
  accessToken: string,
  contrasenaActual: string,
  nuevaContrasena: string
): Promise<ChangePasswordResponse> {
  const response = await fetch('https://tu-dominio.com/api/v1/auth/change-password/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      contrasena_actual: contrasenaActual,
      nueva_contrasena: nuevaContrasena
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Error al cambiar la contraseña');
  }

  return await response.json();
}

// Uso
try {
  const result = await cambiarContrasena(
    accessToken,
    'MiContraseñaActual123',
    'MiNuevaContraseña456'
  );
  console.log('Contraseña cambiada:', result.message);
} catch (error) {
  console.error('Error:', error.message);
}
```

---

### ⚛️ React (con Axios)

```typescript
import axios from 'axios';

interface ChangePasswordData {
  contrasena_actual: string;
  nueva_contrasena: string;
}

const cambiarContrasena = async (
  data: ChangePasswordData,
  accessToken: string
) => {
  try {
    const response = await axios.post(
      'https://tu-dominio.com/api/v1/auth/change-password/',
      data,
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    return response.data;
  } catch (error: any) {
    if (error.response) {
      // Error con respuesta del servidor
      throw new Error(error.response.data.detail || 'Error al cambiar la contraseña');
    } else if (error.request) {
      // Error de red
      throw new Error('Error de conexión. Verifica tu internet.');
    } else {
      // Error al configurar la petición
      throw new Error('Error al procesar la solicitud');
    }
  }
};

// Uso en componente React
const CambiarContrasenaForm = () => {
  const [contrasenaActual, setContrasenaActual] = useState('');
  const [nuevaContrasena, setNuevaContrasena] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const accessToken = localStorage.getItem('access_token'); // O tu método de almacenamiento

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await cambiarContrasena(
        {
          contrasena_actual: contrasenaActual,
          nueva_contrasena: nuevaContrasena
        },
        accessToken!
      );
      
      alert('Contraseña cambiada exitosamente');
      // Limpiar formulario o redirigir
      setContrasenaActual('');
      setNuevaContrasena('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && <div className="error">{error}</div>}
      <input
        type="password"
        value={contrasenaActual}
        onChange={(e) => setContrasenaActual(e.target.value)}
        placeholder="Contraseña actual"
        required
      />
      <input
        type="password"
        value={nuevaContrasena}
        onChange={(e) => setNuevaContrasena(e.target.value)}
        placeholder="Nueva contraseña"
        required
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Cambiando...' : 'Cambiar Contraseña'}
      </button>
    </form>
  );
};
```

---

### 📱 React Native (con Axios)

```typescript
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const cambiarContrasena = async (
  contrasenaActual: string,
  nuevaContrasena: string
) => {
  try {
    // Obtener token del almacenamiento local
    const accessToken = await AsyncStorage.getItem('access_token');
    
    if (!accessToken) {
      throw new Error('No hay sesión activa');
    }

    const response = await axios.post(
      'https://tu-dominio.com/api/v1/auth/change-password/',
      {
        contrasena_actual: contrasenaActual,
        nueva_contrasena: nuevaContrasena
      },
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        }
      }
    );

    return response.data;
  } catch (error: any) {
    if (error.response) {
      const status = error.response.status;
      const detail = error.response.data.detail;
      
      if (status === 401) {
        // Token expirado, redirigir al login
        await AsyncStorage.removeItem('access_token');
        throw new Error('Sesión expirada. Por favor inicia sesión nuevamente.');
      }
      
      throw new Error(detail || 'Error al cambiar la contraseña');
    }
    
    throw new Error('Error de conexión');
  }
};

// Uso en componente React Native
import { useState } from 'react';
import { View, TextInput, Button, Alert } from 'react-native';

const CambiarContrasenaScreen = () => {
  const [contrasenaActual, setContrasenaActual] = useState('');
  const [nuevaContrasena, setNuevaContrasena] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCambiar = async () => {
    if (!contrasenaActual || !nuevaContrasena) {
      Alert.alert('Error', 'Por favor completa todos los campos');
      return;
    }

    setLoading(true);
    try {
      const result = await cambiarContrasena(contrasenaActual, nuevaContrasena);
      Alert.alert('Éxito', result.message);
      setContrasenaActual('');
      setNuevaContrasena('');
    } catch (error: any) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View>
      <TextInput
        secureTextEntry
        value={contrasenaActual}
        onChangeText={setContrasenaActual}
        placeholder="Contraseña actual"
      />
      <TextInput
        secureTextEntry
        value={nuevaContrasena}
        onChangeText={setNuevaContrasena}
        placeholder="Nueva contraseña"
      />
      <Button
        title={loading ? 'Cambiando...' : 'Cambiar Contraseña'}
        onPress={handleCambiar}
        disabled={loading}
      />
    </View>
  );
};
```

---

### 🎯 Vue.js (Composition API)

```typescript
import { ref } from 'vue';
import axios from 'axios';

export const useCambiarContrasena = () => {
  const loading = ref(false);
  const error = ref<string | null>(null);

  const cambiarContrasena = async (
    contrasenaActual: string,
    nuevaContrasena: string,
    accessToken: string
  ) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await axios.post(
        'https://tu-dominio.com/api/v1/auth/change-password/',
        {
          contrasena_actual: contrasenaActual,
          nueva_contrasena: nuevaContrasena
        },
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
          }
        }
      );

      return response.data;
    } catch (err: any) {
      if (err.response) {
        error.value = err.response.data.detail || 'Error al cambiar la contraseña';
      } else {
        error.value = 'Error de conexión';
      }
      throw err;
    } finally {
      loading.value = false;
    }
  };

  return {
    cambiarContrasena,
    loading,
    error
  };
};

// Uso en componente Vue
<script setup lang="ts">
import { ref } from 'vue';
import { useCambiarContrasena } from '@/composables/useCambiarContrasena';

const contrasenaActual = ref('');
const nuevaContrasena = ref('');
const accessToken = localStorage.getItem('access_token') || '';

const { cambiarContrasena, loading, error } = useCambiarContrasena();

const handleSubmit = async () => {
  try {
    const result = await cambiarContrasena(
      contrasenaActual.value,
      nuevaContrasena.value,
      accessToken
    );
    alert('Contraseña cambiada exitosamente');
    contrasenaActual.value = '';
    nuevaContrasena.value = '';
  } catch (err) {
    // Error ya está en error.value
  }
};
</script>
```

---

## ✅ Validación del Frontend (Recomendada)

### Función de Validación de Contraseña

```typescript
interface PasswordValidation {
  isValid: boolean;
  errors: string[];
}

function validarNuevaContrasena(contrasena: string): PasswordValidation {
  const errors: string[] = [];

  if (contrasena.length < 8) {
    errors.push('La contraseña debe tener al menos 8 caracteres');
  }

  if (!/[A-Z]/.test(contrasena)) {
    errors.push('Debe contener al menos una letra mayúscula');
  }

  if (!/[a-z]/.test(contrasena)) {
    errors.push('Debe contener al menos una letra minúscula');
  }

  if (!/[0-9]/.test(contrasena)) {
    errors.push('Debe contener al menos un número');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

function validarContraseñasDiferentes(
  actual: string,
  nueva: string
): boolean {
  return actual !== nueva;
}

// Uso
const nuevaContrasena = 'MiNuevaContraseña123';
const contrasenaActual = 'MiContraseñaActual456';

const validacion = validarNuevaContrasena(nuevaContrasena);
if (!validacion.isValid) {
  console.error('Errores:', validacion.errors);
}

if (!validarContraseñasDiferentes(contrasenaActual, nuevaContrasena)) {
  console.error('La nueva contraseña debe ser diferente a la actual');
}
```

---

## 🔄 Flujo Completo

### 1. Usuario llena el formulario
   - Contraseña actual
   - Nueva contraseña
   - Confirmación de nueva contraseña (opcional, pero recomendado)

### 2. Validación en el Frontend
   - ✅ Campos no vacíos
   - ✅ Nueva contraseña cumple requisitos
   - ✅ Nueva contraseña diferente a la actual
   - ✅ Nueva contraseña coincide con confirmación (si aplica)

### 3. Envío de Petición
   - Obtener Access Token del almacenamiento
   - Enviar POST a `/api/v1/auth/change-password/`
   - Incluir token en header `Authorization`

### 4. Manejo de Respuesta

**Si es exitoso (200):**
- Mostrar mensaje de éxito
- Limpiar formulario
- Opcional: Cerrar sesión y pedir login nuevamente

**Si hay error:**
- Mostrar mensaje de error específico
- Resaltar campos con error
- Permitir reintentar

### 5. Manejo de Token Expirado (401)
- Intentar refrescar token si está disponible
- Si no es posible, redirigir al login
- Limpiar tokens almacenados

---

## 📝 Notas Importantes

1. **Seguridad:**
   - ✅ Nunca almacenes contraseñas en texto plano
   - ✅ Usa HTTPS en producción
   - ✅ Valida en el frontend pero confía en la validación del backend

2. **UX (Experiencia de Usuario):**
   - Muestra indicadores visuales de cumplimiento de requisitos
   - Proporciona feedback inmediato durante la validación
   - Considera cerrar sesión después del cambio exitoso (opcional)

3. **Compatibilidad:**
   - ✅ Funciona para usuarios locales (`origen_datos='local'`)
   - ✅ Funciona para usuarios cliente (`origen_datos='cliente'`)
   - ✅ Funciona en web y mobile
   - ✅ No requiere especificar `usuario_id` (se obtiene del token)

4. **Manejo de Errores:**
   - Siempre maneja errores de red
   - Diferencia entre errores de validación y errores del servidor
   - Proporciona mensajes claros al usuario

---

## 🧪 Ejemplo de Prueba (cURL)

```bash
curl -X POST "https://tu-dominio.com/api/v1/auth/change-password/" \
  -H "Authorization: Bearer tu_access_token_aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "contrasena_actual": "MiContraseñaActual123",
    "nueva_contrasena": "MiNuevaContraseña456"
  }'
```

---

## 📞 Soporte

Si tienes dudas o problemas con la implementación, contacta al equipo de backend.

**Última actualización:** Febrero 2026
