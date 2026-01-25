-- ============================================
-- SISTEMA DE GESTIÓN DE VACACIONES Y PERMISOS
-- VERSIÓN FINAL OPTIMIZADA
-- ============================================
-- Versión: 2.0
-- Fecha: 2026-01-25
-- Base de Datos: SQL Server 2016+
-- Tablas: 7 (Optimizado - Sin ppavac_tipo_permiso)
-- ============================================

USE [bdpla_psf_web]  
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

PRINT '============================================'
PRINT 'INICIANDO CREACIÓN DE TABLAS'
PRINT 'Sistema de Vacaciones y Permisos v2.0'
PRINT '============================================'
PRINT ''

-- ============================================
-- GRUPO 1: TABLAS TRANSACCIONALES (CORE)
-- ============================================

-- ============================================
-- TABLA 1: ppavac_solicitud
-- Descripción: Almacena las solicitudes de vacaciones y permisos
-- Registros esperados: Miles (crecimiento constante)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_solicitud]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[ppavac_solicitud](
        -- IDENTIFICACIÓN
        [id_solicitud] [int] IDENTITY(1,1) NOT NULL,  -- PK: ID único de la solicitud
        
        -- TIPO DE SOLICITUD
        [tipo_solicitud] [char](1) NOT NULL,          -- V=Vacaciones, P=Permiso
        [codigo_permiso] [char](2) NULL,             -- Código del permiso (viene de sp)
                                                       -- NULL si es vacación
                                                       -- Ejemplo: '01', '02'
        
        -- EMPLEADO SOLICITANTE
        [codigo_trabajador] [char](8) NOT NULL,                  -- Código del trabajador que solicita
        
        -- FECHAS DE LA SOLICITUD
        [fecha_inicio] [date] NOT NULL,               -- Fecha inicio del periodo solicitado
        [fecha_fin] [date] NOT NULL,                  -- Fecha fin del periodo solicitado
        [dias_solicitados] [decimal](5,2) NULL,       -- Días solicitados (calculado, puede incluir medios días)
        
        -- DETALLES DE LA SOLICITUD
        [observacion] [varchar](500) NULL,            -- Observaciones/comentarios del empleado
        [motivo] [char](2) NULL,                      -- Código de motivo (opcional, para clasificación)

        -- ESTADO GENERAL DE LA SOLICITUD
        [estado] [char](1) NOT NULL DEFAULT 'P',      -- P=Pendiente, A=Aprobado, R=Rechazado, N=Anulado
                                                       -- Este es el estado GLOBAL de la solicitud
        
        -- AUDITORÍA DE CREACIÓN
        [fecha_registro] [datetime] NOT NULL DEFAULT GETDATE(),  -- Fecha/hora de creación
        [usuario_registro] [char](8) NULL,                       -- Usuario que creó la solicitud
        
        -- AUDITORÍA DE MODIFICACIÓN
        [fecha_modificacion] [datetime] NULL,         -- Fecha/hora de última modificación
        [usuario_modificacion] [char](8) NULL,        -- Usuario que modificó por última vez
        
        -- ANULACIÓN
        [fecha_anulacion] [datetime] NULL,            -- Fecha/hora de anulación
        [usuario_anulacion] [char](8) NULL,           -- Usuario que anuló
        [motivo_anulacion] [varchar](200) NULL,       -- Motivo por el cual se anuló
        
        -- CONTROL INTERNO
        [sregdi] [char](1) NULL DEFAULT 'N',          -- S=Ya se registró en días de descanso, N=No registrado
        [fecha_registro_planilla] [datetime] NULL,    -- Fecha en que se procesó en planilla
        
        CONSTRAINT [PK_ppavac_solicitud] PRIMARY KEY CLUSTERED ([id_solicitud] ASC)
        WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, 
              ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
    ) ON [PRIMARY]
    
    PRINT '✓ Tabla ppavac_solicitud creada exitosamente'
END
ELSE
    PRINT '• Tabla ppavac_solicitud ya existe'
GO

-- ============================================
-- TABLA 2: ppavac_aprobacion
-- Descripción: Registra cada nivel de aprobación y su estado
-- Registros esperados: 2-3x las solicitudes (múltiples niveles)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_aprobacion]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[ppavac_aprobacion](
        -- IDENTIFICACIÓN
        [id_aprobacion] [int] IDENTITY(1,1) NOT NULL,  -- PK: ID único del registro de aprobación
        [id_solicitud] [int] NOT NULL,                 -- FK: Solicitud a la que pertenece
        
        -- NIVEL DE APROBACIÓN
        [nivel] [int] NOT NULL,                        -- Nivel de aprobación: 1=Jefe, 2=Gerente, 3=Director, etc.
                                                        -- El orden importa: nivel 1 aprueba primero
        
        -- APROBADOR
        [codigo_trabajador_aprueba] [char](8) NOT NULL,           -- Código del trabajador que debe/aprobó
        
        -- ESTADO DE ESTA APROBACIÓN
        [estado] [char](1) NOT NULL DEFAULT 'P',       -- P=Pendiente, A=Aprobado, R=Rechazado
        
        -- DETALLE DE LA APROBACIÓN
        [observacion] [varchar](500) NULL,             -- Comentarios del aprobador
        [fecha] [datetime] NULL,                       -- Fecha/hora en que se aprobó/rechazó
        [usuario] [char](8) NULL,                      -- Usuario que realizó la aprobación
        
        -- AUDITORÍA ADICIONAL
        [ip_dispositivo] [varchar](50) NULL,           -- IP o ID del dispositivo desde donde se aprobó
        [fecha_notificado] [datetime] NULL,            -- Fecha en que se notificó al aprobador
        
        CONSTRAINT [PK_ppavac_aprobacion] PRIMARY KEY CLUSTERED ([id_aprobacion] ASC)
        WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, 
              ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
    ) ON [PRIMARY]
    
    PRINT '✓ Tabla ppavac_aprobacion creada exitosamente'
END
ELSE
    PRINT '• Tabla ppavac_aprobacion ya existe'
GO

-- ============================================
-- TABLA 3: ppavac_notificacion
-- Descripción: Gestiona las notificaciones en bandeja del usuario
-- Registros esperados: 5-10x las solicitudes
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_notificacion]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[ppavac_notificacion](
        -- IDENTIFICACIÓN
        [id_notificacion] [int] IDENTITY(1,1) NOT NULL,      -- PK: ID único de la notificación
        [codigo_trabajador] [char](8) NOT NULL,                  -- A quién va dirigida la notificación
        [id_solicitud] [int] NOT NULL,                -- FK: Solicitud relacionada
        
        -- TIPO Y CONTENIDO
        [tipo_notificacion] [char](1) NOT NULL,              -- N=Nueva solicitud, A=Aprobada, R=Rechazada, 
                                                       -- C=Comentario, M=Modificada
        [titulo] [varchar](100) NOT NULL,             -- Título de la notificación
        [mensaje] [varchar](500) NOT NULL,            -- Mensaje descriptivo
        
        -- ESTADO DE LECTURA
        [leido] [char](1) NOT NULL DEFAULT 'N',       -- S=Leído, N=No leído
        [fecha_creacion] [datetime] NOT NULL DEFAULT GETDATE(),  -- Fecha de creación
        [fecha_leido] [datetime] NULL,                -- Fecha en que se marcó como leído
        
        -- INFORMACIÓN ADICIONAL
        [accion_url] [varchar](200) NULL,             -- URL o acción a ejecutar al hacer clic
        [prioridad] [char](1) NULL DEFAULT 'N',       -- A=Alta, N=Normal, B=Baja
        
        CONSTRAINT [PK_ppavac_notificacion] PRIMARY KEY CLUSTERED ([id_notificacion] ASC)
        WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, 
              ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
    ) ON [PRIMARY]
    
    PRINT '✓ Tabla ppavac_notificacion creada exitosamente'
END
ELSE
    PRINT '• Tabla ppavac_notificacion ya existe'
GO

-- ============================================
-- GRUPO 2: TABLAS DE CONFIGURACIÓN
-- ============================================

-- ============================================
-- TABLA 4: ppavac_config_flujo
-- Descripción: Define las reglas de aprobación según criterios
-- Esta tabla trabaja en conjunto con ppavac_jerarquia
-- Registros esperados: 5-15 configuraciones
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_config_flujo]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[ppavac_config_flujo](
        -- IDENTIFICACIÓN
        [id_config] [int] IDENTITY(1,1) NOT NULL,     -- PK: ID único de la configuración
        
        -- TIPO DE SOLICITUD A LA QUE APLICA
        [tipo_solicitud] [char](1) NOT NULL,          -- V=Vacaciones, P=Permiso
        [codigo_permiso] [char](10) NULL,             -- NULL = aplica a todos los permisos
                                                       -- Si tiene valor, solo aplica a ese permiso específico
        
        -- CRITERIOS DE FILTRO (Todos opcionales - NULL = aplica a todos)
        [codigo_area] [char](4) NULL,                       -- Código de área (NULL = todas las áreas)
        [codigo_seccion] [char](4) NULL,                    -- Código de sección (NULL = todas las secciones)
        [codigo_cargo] [char](4) NULL,                      -- Código de cargo (NULL = todos los cargos)
        
        -- CRITERIO POR CANTIDAD DE DÍAS
        [dias_desde] [int] NULL,                      -- Mínimo de días para que aplique (NULL = sin mínimo)
        [dias_hasta] [int] NULL,                      -- Máximo de días para que aplique (NULL = sin máximo)
        
        -- CANTIDAD DE NIVELES DE APROBACIÓN REQUERIDOS
        [niveles_requeridos] [int] NOT NULL DEFAULT 2, -- Cuántos niveles de aprobación se necesitan
                                                        -- Ejemplo: 1, 2, 3, etc.
                                                        -- El sistema buscará esos niveles en ppavac_jerarquia
        
        -- CONTROL DE PRIORIDAD
        [orden] [int] NOT NULL DEFAULT 1,             -- Orden de evaluación (menor = mayor prioridad)
        
        -- VIGENCIA
        [activo] [char](1) NOT NULL DEFAULT 'S',      -- S=Activo, N=Inactivo
        [fecha_desde] [date] NOT NULL DEFAULT GETDATE(),
        [fecha_hasta] [date] NULL,
        
        -- AUDITORÍA
        [usuario_registro] [char](8) NULL,
        [fecha_registro] [datetime] NOT NULL DEFAULT GETDATE(),
        
        -- OBSERVACIONES
        [descripcion] [varchar](200) NULL,            -- Descripción de la regla para documentación
        
        CONSTRAINT [PK_ppavac_config_flujo] PRIMARY KEY CLUSTERED ([id_config] ASC)
        WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, 
              ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
    ) ON [PRIMARY]
    
    PRINT '✓ Tabla ppavac_config_flujo creada exitosamente'
END
ELSE
    PRINT '• Tabla ppavac_config_flujo ya existe'
GO

-- ============================================
-- TABLA 5: ppavac_jerarquia (VERSIÓN MEJORADA)
-- Descripción: Define la estructura de aprobación por área/sección/cargo
-- NO se configura trabajador por trabajador
-- Registros esperados: 10-30 configuraciones
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_jerarquia]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[ppavac_jerarquia](
        -- IDENTIFICACIÓN
        [id_jerarquia] [int] IDENTITY(1,1) NOT NULL,  -- PK: ID único
        
        -- CRITERIOS: Define PARA QUIÉNES aplica esta jerarquía
        [codigo_area] [char](4) NULL,                       -- NULL = todas las áreas
        [codigo_seccion] [char](4) NULL,                    -- NULL = todas las secciones
        [codigo_cargo] [char](4) NULL,                      -- NULL = todos los cargos
                                                       -- Puede usar LIKE: 'VEN%' = todos los vendedores
        
        -- APROBADOR (El supervisor/jefe que aprueba)
        [codigo_trabajador_aprobador] [char](8) NOT NULL,       -- ⭐ Código del trabajador que aprueba
                                                       -- Este ES el aprobador directo
        
        -- TIPO DE RELACIÓN JERÁRQUICA
        [tipo_relacion] [char](1) NOT NULL,           -- J=Jefe Directo, G=Gerente, D=Director
                                                       -- Define el tipo de supervisor
        
        [nivel_jerarquico] [int] NOT NULL,            -- ⭐ 1=Primera aprobación (Jefe)
                                                       --   2=Segunda aprobación (Gerente)
                                                       --   3=Tercera aprobación (Director)
                                                       -- El sistema usa este número para ordenar aprobaciones
        
        -- VIGENCIA
        [activo] [char](1) NOT NULL DEFAULT 'S',      -- S=Activo, N=Inactivo
        [fecha_desde] [date] NOT NULL DEFAULT GETDATE(),
        [fecha_hasta] [date] NULL,
        
        -- AUDITORÍA
        [usuario_registro] [char](8) NULL,
        [fecha_registro] [datetime] NOT NULL DEFAULT GETDATE(),
        [descripcion] [varchar](200) NULL,            -- Descripción de la jerarquía
        
        CONSTRAINT [PK_ppavac_jerarquia] PRIMARY KEY CLUSTERED ([id_jerarquia] ASC)
        WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, 
              ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
    ) ON [PRIMARY]
    
    PRINT '✓ Tabla ppavac_jerarquia creada exitosamente'
END
ELSE
    PRINT '• Tabla ppavac_jerarquia ya existe'
GO

-- ============================================
-- GRUPO 3: TABLAS DE SOPORTE
-- ============================================

-- ============================================
-- TABLA 6: ppavac_dispositivo
-- Descripción: Almacena tokens para notificaciones push
-- Registros esperados: 1-3 por empleado
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_dispositivo]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[ppavac_dispositivo](
        -- IDENTIFICACIÓN
        [id_dispositivo] [int] IDENTITY(1,1) NOT NULL,  -- PK: ID único del dispositivo
        [codigo_trabajador] [char](8) NOT NULL,                    -- Código del trabajador dueño del dispositivo
        
        -- TOKEN PARA PUSH NOTIFICATIONS
        [token_fcm] [varchar](500) NOT NULL,            -- Token de Firebase Cloud Messaging o APNS
                                                         -- Este token es único por dispositivo
        
        -- INFORMACIÓN DEL DISPOSITIVO
        [plataforma] [char](1) NOT NULL,                -- A=Android, I=iOS
        [modelo_dispositivo] [varchar](100) NULL,       -- Ej: "iPhone 13", "Samsung Galaxy S21"
        [version_app] [varchar](20) NULL,               -- Versión de la aplicación instalada
        [version_so] [varchar](20) NULL,                -- Versión del sistema operativo
        
        -- CONTROL DE ACTIVIDAD
        [fecha_registro] [datetime] NOT NULL DEFAULT GETDATE(),  -- Primera vez que se registró
        [fecha_ultimo_acceso] [datetime] NULL,          -- Última vez que accedió a la app
        [activo] [char](1) NOT NULL DEFAULT 'S',        -- S=Activo, N=Inactivo (ej: desinstaló la app)
        
        -- CONFIGURACIÓN DE NOTIFICACIONES
        [notif_nuevas] [char](1) NULL DEFAULT 'S',      -- S=Recibe notif de nuevas solicitudes
        [notif_aprobadas] [char](1) NULL DEFAULT 'S',   -- S=Recibe notif cuando aprueban su solicitud
        [notif_rechazadas] [char](1) NULL DEFAULT 'S',  -- S=Recibe notif cuando rechazan su solicitud
        
        CONSTRAINT [PK_ppavac_dispositivo] PRIMARY KEY CLUSTERED ([id_dispositivo] ASC)
        WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, 
              ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY],
        CONSTRAINT [UK_ppavac_dispositivo_token] UNIQUE NONCLUSTERED ([token_fcm] ASC)
    ) ON [PRIMARY]
    
    PRINT '✓ Tabla ppavac_dispositivo creada exitosamente'
END
ELSE
    PRINT '• Tabla ppavac_dispositivo ya existe'
GO

-- ============================================
-- TABLA 7: ppavac_sustituto
-- Descripción: Define sustitutos cuando un aprobador está ausente
-- Registros esperados: 50-200 (temporales)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_sustituto]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[ppavac_sustituto](
        -- IDENTIFICACIÓN
        [id_sustituto] [int] IDENTITY(1,1) NOT NULL,  -- PK: ID único
        
        -- RELACIÓN DE SUSTITUCIÓN
        [codigo_trabajador_titular] [char](8) NOT NULL,          -- Código del aprobador titular (quien está ausente)
        [codigo_trabajador_sustituto] [char](8) NOT NULL,        -- Código de quien lo sustituye temporalmente
        
        -- PERIODO DE SUSTITUCIÓN
        [fecha_desde] [date] NOT NULL,                -- Inicio del periodo de sustitución
        [fecha_hasta] [date] NOT NULL,                -- Fin del periodo de sustitución
        
        -- DETALLE
        [motivo] [varchar](200) NULL,                 -- Motivo de la sustitución (Ej: "Vacaciones", "Licencia")
        [observacion] [varchar](200) NULL,            -- Observaciones adicionales
        
        -- CONTROL
        [activo] [char](1) NOT NULL DEFAULT 'S',      -- S=Activo, N=Inactivo
        [usuario_registro] [char](8) NULL,
        [fecha_registro] [datetime] NOT NULL DEFAULT GETDATE(),
        
        CONSTRAINT [PK_ppavac_sustituto] PRIMARY KEY CLUSTERED ([id_sustituto] ASC)
        WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, 
              ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
    ) ON [PRIMARY]
    
    PRINT '✓ Tabla ppavac_sustituto creada exitosamente'
END
ELSE
    PRINT '• Tabla ppavac_sustituto ya existe'
GO

-- ============================================
-- FOREIGN KEYS (Integridad Referencial)
-- ============================================
PRINT ''
PRINT 'Creando Foreign Keys...'

-- FK: ppavac_aprobacion -> ppavac_solicitud
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID(N'[dbo].[FK_ppavac_aprobacion_solicitud]'))
BEGIN
    ALTER TABLE [dbo].[ppavac_aprobacion]
    ADD CONSTRAINT [FK_ppavac_aprobacion_solicitud] 
    FOREIGN KEY([id_solicitud]) REFERENCES [dbo].[ppavac_solicitud]([id_solicitud])
    ON DELETE CASCADE
    
    PRINT '✓ FK_ppavac_aprobacion_solicitud creada'
END
GO

-- FK: ppavac_notificacion -> ppavac_solicitud
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID(N'[dbo].[FK_ppavac_notificacion_solicitud]'))
BEGIN
    ALTER TABLE [dbo].[ppavac_notificacion]
    ADD CONSTRAINT [FK_ppavac_notificacion_solicitud] 
    FOREIGN KEY([id_solicitud]) REFERENCES [dbo].[ppavac_solicitud]([id_solicitud])
    ON DELETE CASCADE
    
    PRINT '✓ FK_ppavac_notificacion_solicitud creada'
END
GO

-- ============================================
-- ÍNDICES PARA OPTIMIZAR RENDIMIENTO
-- ============================================
PRINT ''
PRINT 'Creando índices de optimización...'

-- Índices para ppavac_solicitud
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_solicitud]') AND name = N'IX_ppavac_solicitud_codigo_trabajador')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_solicitud_codigo_trabajador] ON [dbo].[ppavac_solicitud]([codigo_trabajador] ASC)
    PRINT '✓ IX_ppavac_solicitud_codigo_trabajador'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_solicitud]') AND name = N'IX_ppavac_solicitud_estado')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_solicitud_estado] ON [dbo].[ppavac_solicitud]([estado] ASC)
    PRINT '✓ IX_ppavac_solicitud_estado'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_solicitud]') AND name = N'IX_ppavac_solicitud_fechas')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_solicitud_fechas] ON [dbo].[ppavac_solicitud]([fecha_inicio] ASC, [fecha_fin] ASC)
    PRINT '✓ IX_ppavac_solicitud_fechas'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_solicitud]') AND name = N'IX_ppavac_solicitud_tipo')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_solicitud_tipo] ON [dbo].[ppavac_solicitud]([tipo_solicitud] ASC, [codigo_permiso] ASC)
    PRINT '✓ IX_ppavac_solicitud_tipo'
END
GO

-- Índices para ppavac_aprobacion
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_aprobacion]') AND name = N'IX_ppavac_aprobacion_solicitud')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_aprobacion_solicitud] ON [dbo].[ppavac_aprobacion]([id_solicitud] ASC)
    PRINT '✓ IX_ppavac_aprobacion_solicitud'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_aprobacion]') AND name = N'IX_ppavac_aprobacion_aprobador')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_aprobacion_aprobador] ON [dbo].[ppavac_aprobacion]([codigo_trabajador_aprueba] ASC, [estado] ASC)
    PRINT '✓ IX_ppavac_aprobacion_aprobador'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_aprobacion]') AND name = N'IX_ppavac_aprobacion_nivel')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_aprobacion_nivel] ON [dbo].[ppavac_aprobacion]([nivel] ASC, [estado] ASC)
    PRINT '✓ IX_ppavac_aprobacion_nivel'
END
GO

-- Índices para ppavac_notificacion
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_notificacion]') AND name = N'IX_ppavac_notificacion_codigo_trabajador_leido')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_notificacion_codigo_trabajador_leido] ON [dbo].[ppavac_notificacion]([codigo_trabajador] ASC, [leido] ASC)
    PRINT '✓ IX_ppavac_notificacion_codigo_trabajador_leido'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_notificacion]') AND name = N'IX_ppavac_notificacion_fecha')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_notificacion_fecha] ON [dbo].[ppavac_notificacion]([fecha_creacion] DESC)
    PRINT '✓ IX_ppavac_notificacion_fecha'
END
GO

-- Índices para ppavac_config_flujo
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_config_flujo]') AND name = N'IX_ppavac_config_flujo_tipo')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_config_flujo_tipo] ON [dbo].[ppavac_config_flujo]([tipo_solicitud] ASC, [activo] ASC)
    PRINT '✓ IX_ppavac_config_flujo_tipo'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_config_flujo]') AND name = N'IX_ppavac_config_flujo_area')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_config_flujo_area] ON [dbo].[ppavac_config_flujo]([codigo_area] ASC)
    PRINT '✓ IX_ppavac_config_flujo_area'
END
GO

-- Índices para ppavac_jerarquia
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_jerarquia]') AND name = N'IX_ppavac_jerarquia_area')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_jerarquia_area] ON [dbo].[ppavac_jerarquia]([codigo_area] ASC)
    PRINT '✓ IX_ppavac_jerarquia_area'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_jerarquia]') AND name = N'IX_ppavac_jerarquia_seccion')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_jerarquia_seccion] ON [dbo].[ppavac_jerarquia]([codigo_seccion] ASC)
    PRINT '✓ IX_ppavac_jerarquia_seccion'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_jerarquia]') AND name = N'IX_ppavac_jerarquia_cargo')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_jerarquia_cargo] ON [dbo].[ppavac_jerarquia]([codigo_cargo] ASC)
    PRINT '✓ IX_ppavac_jerarquia_cargo'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_jerarquia]') AND name = N'IX_ppavac_jerarquia_nivel')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_jerarquia_nivel] ON [dbo].[ppavac_jerarquia]([nivel_jerarquico] ASC, [activo] ASC)
    PRINT '✓ IX_ppavac_jerarquia_nivel'
END
GO

-- Índices para ppavac_dispositivo
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_dispositivo]') AND name = N'IX_ppavac_dispositivo_codigo_trabajador')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_dispositivo_codigo_trabajador] ON [dbo].[ppavac_dispositivo]([codigo_trabajador] ASC, [activo] ASC)
    PRINT '✓ IX_ppavac_dispositivo_codigo_trabajador'
END
GO

-- Índices para ppavac_sustituto
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_sustituto]') AND name = N'IX_ppavac_sustituto_titular')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_sustituto_titular] ON [dbo].[ppavac_sustituto]([codigo_trabajador_titular] ASC, [activo] ASC)
    PRINT '✓ IX_ppavac_sustituto_titular'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'[dbo].[ppavac_sustituto]') AND name = N'IX_ppavac_sustituto_fechas')
BEGIN
    CREATE NONCLUSTERED INDEX [IX_ppavac_sustituto_fechas] ON [dbo].[ppavac_sustituto]([fecha_desde] ASC, [fecha_hasta] ASC)
    PRINT '✓ IX_ppavac_sustituto_fechas'
END
GO

-- ============================================
-- DATOS INICIALES: Configuraciones Básicas
-- ============================================
PRINT ''
PRINT '============================================'
PRINT 'Insertando configuraciones iniciales...'
PRINT '============================================'

-- Configuración básica para VACACIONES
IF NOT EXISTS (SELECT 1 FROM ppavac_config_flujo WHERE tipo_solicitud = 'V' AND codigo_area IS NULL AND niveles_requeridos = 2)
BEGIN
    INSERT INTO [dbo].[ppavac_config_flujo]
    (tipo_solicitud, codigo_permiso, codigo_area, codigo_seccion, codigo_cargo, dias_desde, dias_hasta, niveles_requeridos, orden, descripcion)
    VALUES 
    ('V', NULL, NULL, NULL, NULL, NULL, NULL, 2, 1, 'Configuración general para vacaciones - 2 niveles de aprobación')
    PRINT '✓ Config: Vacaciones - Regla General (2 niveles)'
END
GO

-- Configuración básica para PERMISOS (hasta 3 días)
IF NOT EXISTS (SELECT 1 FROM ppavac_config_flujo WHERE tipo_solicitud = 'P' AND codigo_area IS NULL AND dias_hasta = 3)
BEGIN
    INSERT INTO [dbo].[ppavac_config_flujo]
    (tipo_solicitud, codigo_permiso, codigo_area, codigo_seccion, codigo_cargo, dias_desde, dias_hasta, niveles_requeridos, orden, descripcion)
    VALUES 
    ('P', NULL, NULL, NULL, NULL, NULL, 3, 1, 1, 'Permisos cortos (≤3 días) - 1 nivel de aprobación')
    PRINT '✓ Config: Permisos cortos (≤3 días) - 1 nivel'
END
GO

-- Configuración para PERMISOS largos (más de 3 días)
IF NOT EXISTS (SELECT 1 FROM ppavac_config_flujo WHERE tipo_solicitud = 'P' AND codigo_area IS NULL AND dias_desde = 4)
BEGIN
    INSERT INTO [dbo].[ppavac_config_flujo]
    (tipo_solicitud, codigo_permiso, codigo_area, codigo_seccion, codigo_cargo, dias_desde, dias_hasta, niveles_requeridos, orden, descripcion)
    VALUES 
    ('P', NULL, NULL, NULL, NULL, 4, NULL, 2, 1, 'Permisos largos (>3 días) - 2 niveles de aprobación')
    PRINT '✓ Config: Permisos largos (>3 días) - 2 niveles'
END
GO

-- ============================================
-- EJEMPLO DE JERARQUÍA INICIAL
-- ============================================
PRINT ''
PRINT 'Insertando ejemplo de jerarquía...'
PRINT '(IMPORTANTE: Debes configurar según tu estructura organizacional)'

-- Ejemplo: Regla general para toda la empresa
-- NOTA: Debes cambiar los códigos de trabajador por los reales
/*
INSERT INTO [dbo].[ppavac_jerarquia]
(carea, cseccion, ccargo, ctraba_supervisor, tipo_relacion, nivel_jerarquico, descripcion)
VALUES 
(NULL, NULL, NULL, '000001', 'J', 1, 'Regla general - Nivel 1: Jefe de RRHH (EJEMPLO)'),
(NULL, NULL, NULL, '000002', 'D', 2, 'Regla general - Nivel 2: Gerente General (EJEMPLO)')

PRINT '✓ Jerarquía de ejemplo creada'
PRINT '  ⚠️ IMPORTANTE: Configura la jerarquía real de tu empresa'
*/

PRINT '  ℹ️  Jerarquía no insertada - Debes configurarla manualmente'

-- ============================================
-- RESUMEN FINAL
-- ============================================
PRINT ''
PRINT '============================================'
PRINT 'SCRIPT COMPLETADO EXITOSAMENTE'
PRINT '============================================'
PRINT ''
PRINT 'TABLAS CREADAS (7):'
PRINT '  ✓ 1. ppavac_solicitud        - Solicitudes de vacaciones/permisos'
PRINT '  ✓ 2. ppavac_aprobacion       - Registros de aprobación por nivel'
PRINT '  ✓ 3. ppavac_notificacion     - Notificaciones para usuarios'
PRINT '  ✓ 4. ppavac_config_flujo     - Configuración de niveles requeridos'
PRINT '  ✓ 5. ppavac_jerarquia        - Estructura de aprobadores (área/sección/cargo)'
PRINT '  ✓ 6. ppavac_dispositivo      - Tokens para push notifications'
PRINT '  ✓ 7. ppavac_sustituto        - Sustitutos temporales'
PRINT ''
PRINT 'CONFIGURACIONES INICIALES:'
PRINT '  ✓ 3 Configuraciones básicas de flujo'
PRINT '  ℹ️  Jerarquía pendiente de configuración'
PRINT ''
PRINT 'PRÓXIMOS PASOS:'
PRINT '  1. Configurar ppavac_jerarquia con tu estructura organizacional'
PRINT '  2. Ajustar ppavac_config_flujo según tus reglas de negocio'
PRINT '  3. Tu tabla de tipos de permiso se manejará desde tu SP'
PRINT '  4. Implementar los Stored Procedures de negocio'
PRINT '  5. Configurar el servicio de push notifications (Firebase)'
PRINT ''
PRINT '============================================'
PRINT 'NOTAS IMPORTANTES:'
PRINT '============================================'
PRINT ''
PRINT '📌 Campo codigo_permiso:'
PRINT '   - En ppavac_solicitud.codigo_permiso guardas el código que viene de TU tabla'
PRINT '   - Ejemplo: ''PERM001'', ''PERM_SALUD'', etc.'
PRINT '   - Tu SP manejará la descripción desde tu tabla existente'
PRINT ''
PRINT '📌 ppavac_jerarquia:'
PRINT '   - Define aprobadores por área/sección/cargo'
PRINT '   - NO por trabajador individual'
PRINT '   - ctraba_supervisor ES el aprobador directo'
PRINT '   - nivel_jerarquico define el orden (1, 2, 3...)'
PRINT ''
PRINT '📌 ppavac_config_flujo:'
PRINT '   - Define CUÁNTOS niveles se necesitan'
PRINT '   - El sistema busca esos niveles en ppavac_jerarquia'
PRINT '   - Ejemplo: niveles_requeridos=2 → busca nivel 1 y 2'
PRINT ''
PRINT '============================================'
GO


-- Áreas
CREATE VIEW vw_tareas00 AS
SELECT careas, dareas 
FROM [192.168.1.3].[bdpla_psf].[dbo].tareas00 
WHERE sareas='A'

-- Secciones
CREATE VIEW vw_tsecci00 AS
SELECT csecci, dsecci 
FROM [192.168.1.3].[bdpla_psf].[dbo].tsecci00 
WHERE ssecci='A'

-- Cargos
CREATE VIEW vw_tcargo00 AS
SELECT ccargo, dcargo 
FROM [192.168.1.3].[bdpla_psf].[dbo].tcargo00 
WHERE scargo='A'

-- Configuraciones (Tipos de Permiso)
CREATE VIEW vw_mconfa00 AS
SELECT cconfa, dconfa 
FROM [192.168.1.3].[bdpla_psf].[dbo].mconfa00 
WHERE sconfa='A' 
AND cconfa IN ('03','04','07','08','10','11')

-- Trabajadores (Personal)
CREATE VIEW vw_mtraba10 AS
select ctraba,rtrim(dappat)+' '+rtrim(dapmat)+' '+rtrim(dnombr) as dtraba
		,careas,csecci,ccargo, nlbele as numdni
from [192.168.1.3].[bdpla_psf].[dbo].mtraba00 where straba='A' and svigen='S'

-- Saldo de Vacaciones
CREATE VIEW vw_ppavac_saldo_vacaciones
AS
SELECT
    -- Identificación
    t.ctraba AS codigo_trabajador,    

    -- Derechos totales de vacaciones
    CAST(30.00 AS DECIMAL(5,2)) AS dias_asignados_totales,

    -- Consumos
    CAST(10.00 AS DECIMAL(5,2)) AS dias_usados,
    CAST(2.00  AS DECIMAL(5,2)) AS dias_pendientes,

    -- Resultado final
    CAST(18.00 AS DECIMAL(5,2)) AS saldo_disponible

FROM mtraba10 t

GO