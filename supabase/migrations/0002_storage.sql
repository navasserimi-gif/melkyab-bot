-- Storage-Buckets für Wohnungsbilder (öffentlich) und Dokumente (privat, §6/§17).
-- Sensible Dokumente werden nie öffentlich ausgeliefert — nur über kurzlebige
-- Signed URLs, die serverseitig nach Rechteprüfung erzeugt werden.

insert into storage.buckets (id, name, public)
values ('property-images', 'property-images', true)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('applicant-documents', 'applicant-documents', false)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public)
values ('property-documents', 'property-documents', false)
on conflict (id) do nothing;

-- property-images: öffentlich lesbar (Bucket ist public), Schreiben nur admin.
-- Pfadkonvention: {property_id}/{filename}
create policy property_images_bucket_write on storage.objects for insert
  with check (bucket_id = 'property-images' and public.is_admin());
create policy property_images_bucket_update on storage.objects for update
  using (bucket_id = 'property-images' and public.is_admin());
create policy property_images_bucket_delete on storage.objects for delete
  using (bucket_id = 'property-images' and public.is_admin());

-- applicant-documents: privat. Pfadkonvention: {applicant_id}/{filename}
create policy applicant_documents_bucket_select on storage.objects for select
  using (
    bucket_id = 'applicant-documents' and (
      public.is_staff() or exists (
        select 1 from public.applicants a
        where a.id::text = (storage.foldername(name))[1] and a.user_id = auth.uid()
      )
    )
  );

create policy applicant_documents_bucket_insert on storage.objects for insert
  with check (
    bucket_id = 'applicant-documents' and (
      public.is_staff() or exists (
        select 1 from public.applicants a
        where a.id::text = (storage.foldername(name))[1] and a.user_id = auth.uid()
      )
    )
  );

create policy applicant_documents_bucket_delete on storage.objects for delete
  using (bucket_id = 'applicant-documents' and public.is_staff());

-- property-documents: privat, ausschließlich Staff. Pfadkonvention: {property_id}/{filename}
create policy property_documents_bucket_all on storage.objects for all
  using (bucket_id = 'property-documents' and public.is_staff())
  with check (bucket_id = 'property-documents' and public.is_staff());
