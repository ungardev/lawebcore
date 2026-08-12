-- =================================================================
-- LA WEB CORE - Create user: Ignacio Chacón (admin_general)
-- =================================================================
-- Ejecutar directamente en Railway SQL Editor (NO en Supabase SQL Editor)
-- Conecta a: Railway PostgreSQL (postgres.railway.internal:5432)
--
-- Este script:
--   1. Añade columna password_hash a users (IF NOT EXISTS)
--   2. Inserta/actualiza el usuario con bcrypt hash
--   3. Asigna rol admin_general
--   4. Verifica el resultado
--
-- LOGIN: POST /api/v1/auth/login con email + password
-- =================================================================

-- 1. Añadir columna password_hash si no existe (idempotente)
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- 2. Crear usuario e asignar rol admin_general
DO $$
DECLARE
    new_user_id UUID := gen_random_uuid();
    new_role_id UUID;
    password_hash_value TEXT := '$2b$12$l5kMszTHApZEIxSH3UK/6emszkiZlEm91nLOSFkuSLlYoOHMto2nG';
BEGIN
    -- Insertar usuario (ON CONFLICT para ser idempotente)
    INSERT INTO public.users (
        id, email, full_name, status, job_title,
        locale, timezone, metadata,
        created_at, updated_at, password_hash
    )
    VALUES (
        new_user_id,
        'ignacio.chacon@hacemosloquenosgusta.com',
        'Ignacio Chacón',
        'active',
        'Administrador General',
        'es-VE',
        'America/Caracas',
        '{"created_by": "scripts/create_user_ignacio.sql", "note": "Initial admin via SQL seed"}',
        NOW(),
        NOW(),
        password_hash_value
    )
    ON CONFLICT (email) DO UPDATE SET
        full_name = EXCLUDED.full_name,
        status = 'active',
        job_title = EXCLUDED.job_title,
        password_hash = EXCLUDED.password_hash,
        updated_at = NOW();

    -- Obtener el ID del usuario (ya sea nuevo o existente)
    SELECT u.id INTO new_user_id
    FROM public.users u
    WHERE u.email = 'ignacio.chacon@hacemosloquenosgusta.com';

    -- Asignar rol admin_general
    SELECT id INTO new_role_id FROM public.roles WHERE code = 'admin_general';

    IF new_role_id IS NOT NULL THEN
        INSERT INTO public.user_roles (user_id, role_id, business_unit_id, granted_by, granted_at)
        VALUES (new_user_id, new_role_id, NULL, new_user_id, NOW())
        ON CONFLICT (user_id, role_id, business_unit_id) DO NOTHING;
    END IF;

    RAISE NOTICE 'Usuario creado/actualizado: ignacio.chacon@hacemosloquenosgusta.com (id=%)', new_user_id;
    RAISE NOTICE 'Rol asignado: admin_general (role_id=%)', new_role_id;
END $$;

-- 3. Verificación final
SELECT
    u.id,
    u.email,
    u.full_name,
    u.status,
    u.job_title,
    u.created_at,
    u.password_hash IS NOT NULL AS has_password,
    r.code AS role_code
FROM public.users u
LEFT JOIN public.user_roles ur ON ur.user_id = u.id
LEFT JOIN public.roles r ON r.id = ur.role_id
WHERE u.email = 'ignacio.chacon@hacemosloquenosgusta.com';
