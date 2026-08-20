import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

/**
 * Supabase-Client für Server Components/Actions. Verwendet den anon-Key +
 * die Session-Cookies des Nutzers — RLS greift also immer, genau wie im
 * Browser. Niemals den Service-Role-Key hier verwenden.
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            for (const { name, value, options } of cookiesToSet) {
              cookieStore.set(name, value, options);
            }
          } catch {
            // In Server Components (nicht Server Actions/Route Handlers) darf
            // kein Cookie gesetzt werden — die Middleware erneuert die
            // Session in diesem Fall.
          }
        },
      },
    },
  );
}
