-- 標籤改名（owner 專用）：同時改 notes.tags 與 tag_vocab
create or replace function public.rename_tag(p_family text, p_old text, p_new text) returns int
language plpgsql security definer set search_path = public as $$
declare n int;
begin
  if not public.is_owner() then raise exception '只有 owner 可以改標籤'; end if;
  update public.notes set tags = array_replace(tags, p_family || '/' || p_old, p_family || '/' || p_new)
    where tags @> array[p_family || '/' || p_old];
  get diagnostics n = row_count;
  update public.tag_vocab set value = p_new where family = p_family and value = p_old;
  return n;
end $$;
grant execute on function public.rename_tag(text, text, text) to authenticated;

-- 這一輪的三個用途標籤改名
update public.notes set tags = array_replace(tags, '用途/照著做', '用途/實作教學');
update public.notes set tags = array_replace(tags, '用途/建立觀念', '用途/觀念建立');
update public.notes set tags = array_replace(tags, '用途/案例故事', '用途/案例分享');
update public.tag_vocab set value = '實作教學' where family = '用途' and value = '照著做';
update public.tag_vocab set value = '觀念建立' where family = '用途' and value = '建立觀念';
update public.tag_vocab set value = '案例分享' where family = '用途' and value = '案例故事';
select value, (select count(*) from public.notes where tags @> array['用途/' || value]) as n from public.tag_vocab where family = '用途';
