-- ============================================================
-- Importar 14 influencers de Nescafe Dolce Gusto
-- source=manual, country=VE, language=es
-- ============================================================

-- ---- Armando Poyo (@armandopoyo) 423K MACRO ----
DO $$
DECLARE
  inf_armando UUID := gen_random_uuid();
  soc_armando UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_armando, 'Armando Poyo', 'VE', 'MACRO', '@armandopoyo', 'https://www.instagram.com/armandopoyo/', 'Comedia y vlogs en Venezuela', ARRAY['comedia','vlogs','lifestyle'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_armando, inf_armando, 'instagram', '@armandopoyo', 'https://www.instagram.com/armandopoyo/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_armando, soc_armando, CURRENT_DATE, 423000);
END $$;

-- ---- Sofia Saavedra (@sognis) 366K MACRO ----
DO $$
DECLARE
  inf_sofia UUID := gen_random_uuid();
  soc_sofia UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_sofia, 'Sofia Saavedra', 'VE', 'MACRO', '@sognis', 'https://www.instagram.com/sognis/', 'Vlogs, fashion y lifestyle', ARRAY['vlogs','fashion','lifestyle'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_sofia, inf_sofia, 'instagram', '@sognis', 'https://www.instagram.com/sognis/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_sofia, soc_sofia, CURRENT_DATE, 366000);
END $$;

-- ---- Isaias Landaeta (@isaiaslandaeta) 331K MACRO ----
DO $$
DECLARE
  inf_isaias UUID := gen_random_uuid();
  soc_isaias UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_isaias, 'Isaias Landaeta', 'VE', 'MACRO', '@isaiaslandaeta', 'https://www.instagram.com/isaiaslandaeta/', 'Naturaleza, vlogs, travel y fotografia', ARRAY['naturaleza','vlogs','travel','fotografia'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_isaias, inf_isaias, 'instagram', '@isaiaslandaeta', 'https://www.instagram.com/isaiaslandaeta/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_isaias, soc_isaias, CURRENT_DATE, 331000);
END $$;

-- ---- Diego Vallenilla (@dieguisimo) 324K MACRO ----
DO $$
DECLARE
  inf_diego UUID := gen_random_uuid();
  soc_diego UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_diego, 'Diego Vallenilla', 'VE', 'MACRO', '@dieguisimo', 'https://www.instagram.com/dieguisimo/', 'Fotografia, guia turistico e historia', ARRAY['fotografia','turismo','historia','lifestyle'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_diego, inf_diego, 'instagram', '@dieguisimo', 'https://www.instagram.com/dieguisimo/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_diego, soc_diego, CURRENT_DATE, 324000);
END $$;

-- ---- Alejandra Guzman (@alegmassiani) 163K MID ----
DO $$
DECLARE
  inf_ale UUID := gen_random_uuid();
  soc_ale UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_ale, 'Alejandra Guzman', 'VE', 'MID', '@alegmassiani', 'https://www.instagram.com/alegmassiani/', 'Lifestyle y vlogs', ARRAY['lifestyle','vlogs'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_ale, inf_ale, 'instagram', '@alegmassiani', 'https://www.instagram.com/alegmassiani/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_ale, soc_ale, CURRENT_DATE, 163000);
END $$;

-- ---- Irina bozzone (@irinabozzone) 116K MID ----
DO $$
DECLARE
  inf_irina UUID := gen_random_uuid();
  soc_irina UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_irina, 'Irina bozzone', 'VE', 'MID', '@irinabozzone', 'https://www.instagram.com/irinabozzone/', 'Lifestyle y vlogs', ARRAY['lifestyle','vlogs'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_irina, inf_irina, 'instagram', '@irinabozzone', 'https://www.instagram.com/irinabozzone/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_irina, soc_irina, CURRENT_DATE, 116000);
END $$;

-- ---- Ana Otero (@anaiotero) 82K MICRO ----
DO $$
DECLARE
  inf_ana UUID := gen_random_uuid();
  soc_ana UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_ana, 'Ana Otero', 'VE', 'MICRO', '@anaiotero', 'https://www.instagram.com/anaiotero/', 'Lifestyle', ARRAY['lifestyle'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_ana, inf_ana, 'instagram', '@anaiotero', 'https://www.instagram.com/anaiotero/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_ana, soc_ana, CURRENT_DATE, 82000);
END $$;

-- ---- Patricia Carreno (@patrilucia) 32.8K MICRO ----
DO $$
DECLARE
  inf_patricia UUID := gen_random_uuid();
  soc_patricia UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_patricia, 'Patricia Carreno', 'VE', 'MICRO', '@patrilucia', 'https://www.instagram.com/patrilucia/', 'Lifestyle', ARRAY['lifestyle'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_patricia, inf_patricia, 'instagram', '@patrilucia', 'https://www.instagram.com/patrilucia/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_patricia, soc_patricia, CURRENT_DATE, 32800);
END $$;

-- ---- Lulu Dow (@cocinandoconlulu) 6.6K NANO ----
DO $$
DECLARE
  inf_lulu UUID := gen_random_uuid();
  soc_lulu UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_lulu, 'Lulu Dow', 'VE', 'NANO', '@cocinandoconlulu', 'https://www.instagram.com/cocinandoconlulu/', 'Cocina', ARRAY['cocina'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_lulu, inf_lulu, 'instagram', '@cocinandoconlulu', 'https://www.instagram.com/cocinandoconlulu/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_lulu, soc_lulu, CURRENT_DATE, 6623);
END $$;

-- ---- Gastro.no.mia (@gastro.no.mia) 312K MACRO ----
DO $$
DECLARE
  inf_gastro UUID := gen_random_uuid();
  soc_gastro UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_gastro, 'Gastro.no.mia', 'VE', 'MACRO', '@gastro.no.mia', 'https://www.instagram.com/gastro.no.mia/', 'Cocina', ARRAY['cocina'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_gastro, inf_gastro, 'instagram', '@gastro.no.mia', 'https://www.instagram.com/gastro.no.mia/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_gastro, soc_gastro, CURRENT_DATE, 312000);
END $$;

-- ---- Isabel Bermudez (@isabermudezfebres) 235K MID ----
DO $$
DECLARE
  inf_isabel UUID := gen_random_uuid();
  soc_isabel UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_isabel, 'Isabel Bermudez', 'VE', 'MID', '@isabermudezfebres', 'https://www.instagram.com/isabermudezfebres/', 'Finanzas', ARRAY['finanzas','lifestyle'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_isabel, inf_isabel, 'instagram', '@isabermudezfebres', 'https://www.instagram.com/isabermudezfebres/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_isabel, soc_isabel, CURRENT_DATE, 235000);
END $$;

-- ---- Ina Cocina (@inacocina) 165K MID ----
DO $$
DECLARE
  inf_ina UUID := gen_random_uuid();
  soc_ina UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_ina, 'Ina Cocina', 'VE', 'MID', '@inacocina', 'https://www.instagram.com/inacocina/', 'Cocina', ARRAY['cocina'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_ina, inf_ina, 'instagram', '@inacocina', 'https://www.instagram.com/inacocina/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_ina, soc_ina, CURRENT_DATE, 165000);
END $$;

-- ---- Maribel Petrola (@maribelpetrola) 99.3K MICRO ----
DO $$
DECLARE
  inf_maribel UUID := gen_random_uuid();
  soc_maribel UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_maribel, 'Maribel Petrola', 'VE', 'MICRO', '@maribelpetrola', 'https://www.instagram.com/maribelpetrola/', 'Lifestyle y cocina', ARRAY['lifestyle','cocina'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_maribel, inf_maribel, 'instagram', '@maribelpetrola', 'https://www.instagram.com/maribelpetrola/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_maribel, soc_maribel, CURRENT_DATE, 99300);
END $$;

-- ---- Mercedes Grau (@mercedesgraureposteria) 99.6K MICRO ----
DO $$
DECLARE
  inf_mercedes UUID := gen_random_uuid();
  soc_mercedes UUID := gen_random_uuid();
BEGIN
  INSERT INTO influencers (id, full_name, country, primary_tier, primary_handle, avatar_url, bio, content_niches, languages, status, source, created_at, updated_at)
  VALUES (inf_mercedes, 'Mercedes Grau', 'VE', 'MICRO', '@mercedesgraureposteria', 'https://www.instagram.com/mercedesgraureposteria/', 'Lifestyle y cocina', ARRAY['lifestyle','cocina'], ARRAY['es'], 'active', 'manual', NOW(), NOW());

  INSERT INTO influencer_social_accounts (id, influencer_id, platform, handle, url, is_primary, created_at, updated_at)
  VALUES (soc_mercedes, inf_mercedes, 'instagram', '@mercedesgraureposteria', 'https://www.instagram.com/mercedesgraureposteria/', true, NOW(), NOW());

  INSERT INTO influencer_metrics_snapshot (influencer_id, social_account_id, snapshot_date, followers)
  VALUES (inf_mercedes, soc_mercedes, CURRENT_DATE, 99600);
END $$;
