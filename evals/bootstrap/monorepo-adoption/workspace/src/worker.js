const ROUTES = {
  '/health': () => new Response('ok'),
  '/digest': async (env) => {
    const digest = await env.DIGESTS.get('latest');
    return new Response(digest ?? 'no digest yet', { status: digest ? 200 : 404 });
  },
};

export function route(pathname) {
  return ROUTES[pathname] ?? null;
}

export default {
  async fetch(request, env) {
    const handler = route(new URL(request.url).pathname);
    if (!handler) return new Response('not found', { status: 404 });
    return handler(env);
  },
};
