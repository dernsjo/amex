# Frontend

Vite + React 19 + TypeScript.

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # type-checks, then builds to dist/
```

The API URL defaults to `http://localhost:8000`; override with `VITE_API_URL`
in `.env.local` (see `.env.example`).

## Design
The look follows the Leva brand kit (`../brand/kit/project/README.md`): one
stylesheet of tokens and classes in `src/styles.css`, shared pieces (the logo,
`ShareBar`, `Segmented`, `MonthStepper`, confirm/prompt dialogs) in
`src/components/ui.tsx`. The views live in the URL hash (`#overview`,
`#transactions`, `#budget`, `#settle`, `#import`, `#setup`).

To see the signed-in app without a backend or a Supabase login, run `npm run dev`
and open `/demo.html` (add `?household=10` for the sample household). It answers
every API read with invented sample data from `src/demo/mock.ts`; writes do nothing.

## Sign-in
Supabase handles sign-in (`src/components/Login.tsx`): Google, email and password,
or a magic link. All of them end in the same Supabase session, so the backend
doesn't care which was used, and the same verified email is the same user.
Set up in the Supabase dashboard:
- **Authentication → URL Configuration:** add the app's URL (e.g.
  `http://localhost:5173`) under Redirect URLs; Google, confirmation and reset
  emails all return there.
- **Authentication → Providers → Email:** keep "Confirm email" on. Someone added
  to a household before signing up only takes over that membership with a
  verified email.
- **Authentication → Providers → Google:** paste the client ID and secret of a
  Google Cloud OAuth client (type "Web application") whose authorized redirect URI
  is `https://<project-ref>.supabase.co/auth/v1/callback`.

Signed-in users can set a password with "Set password", so magic-link users can
switch. "Forgot password?" emails a link that signs you in and asks for a new one.
