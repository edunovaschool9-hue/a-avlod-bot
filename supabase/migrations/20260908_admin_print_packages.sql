create or replace function public.ep_print_komplekt(
  p_token text,
  p_daraja integer default null,
  p_sana date default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public', 'pg_temp'
as $function$
declare
  v_admin public.ep_odam;
  v_sana date;
begin
  v_admin := public.ep__rol(p_token, 'admin');
  if p_daraja is not null and p_daraja not between 5 and 7 then
    raise exception 'SINF';
  end if;

  v_sana := coalesce(p_sana, (now() at time zone 'Asia/Tashkent')::date);

  return jsonb_build_object(
    'ok', true,
    'sana', v_sana,
    'sinflar', coalesce((
      select jsonb_agg(
        jsonb_build_object(
          'id', c.id,
          'nom', c.nom,
          'daraja', c.daraja,
          'til', c.til,
          'oquvchilar', c.oquvchilar,
          'fanlar', (
            select jsonb_agg(
              jsonb_build_object(
                'kod', f.kod,
                'nom', case when c.til = 'ru' then f.nom_ru else f.nom_uz end,
                'savollar', coalesce((
                  select jsonb_agg(
                    jsonb_build_object(
                      'id', q.id,
                      'savol', q.savol,
                      'a', q.a,
                      'b', q.b,
                      'c', q.c,
                      'd', q.d
                    ) order by q.tartib
                  )
                  from (
                    select s.id, s.savol, s.a, s.b, s.c, s.d,
                           md5(v_sana::text || ':' || c.id::text || ':' || f.kod || ':' || s.id::text) as tartib
                    from public.ep_savol s
                    where s.fan_id = any(f.fan_ids)
                      and s.daraja = c.daraja
                      and s.faol
                      and s.tasdiq
                      and (s.til = c.til or s.til = 'ikki')
                    order by md5(v_sana::text || ':' || c.id::text || ':' || f.kod || ':' || s.id::text)
                    limit 5
                  ) q
                ), '[]'::jsonb)
              ) order by f.tartib
            )
            from (values
              (1, 'matematika', array[1]::integer[], 'Matematika', 'Математика'),
              (2, 'tarix', array[12]::integer[], 'Tarix', 'История'),
              (3, 'tabiiy', array[8,9,10]::integer[], 'Tabiiy fan', 'Естественные науки'),
              (4, 'rus_tili', array[4]::integer[], 'Rus tili', 'Русский язык'),
              (5, 'ona_tili', array[2]::integer[], 'Ona tili va adabiyoti', 'Родной язык и литература')
            ) as f(tartib, kod, fan_ids, nom_uz, nom_ru)
          )
        ) order by c.daraja, c.nom
      )
      from (
        select s.id, s.nom, s.daraja,
               case when lower(coalesce(s.til, 'uz')) = 'ru' then 'ru' else 'uz' end as til,
               count(o.id)::integer as oquvchilar
        from public.ep_sinf s
        left join public.ep_oquvchi o on o.sinf_id = s.id and o.faol
        where s.faol
          and s.daraja between 5 and 7
          and (p_daraja is null or s.daraja = p_daraja)
        group by s.id, s.nom, s.daraja, s.til
      ) c
    ), '[]'::jsonb)
  );
end
$function$;

revoke all on function public.ep_print_komplekt(text, integer, date) from public;
grant execute on function public.ep_print_komplekt(text, integer, date) to anon, authenticated;
