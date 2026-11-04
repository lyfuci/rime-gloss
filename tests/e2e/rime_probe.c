/* Deploys a Rime user directory with the real librime, selects a schema,
 * sets switch options, types a key sequence and prints the candidates as
 * "text<TAB>comment" lines. Used by tests/e2e/run.sh.
 *
 * usage: rime_probe SHARED_DIR USER_DIR SCHEMA KEYS [option=0|1 ...]
 * build: cc -o rime_probe rime_probe.c -lrime -ldl
 *
 * Frontends such as Weasel link librime-lua in; here the plugin is a separate
 * library, so RIME_PROBE_LUA_PLUGIN names it and the probe loads it first.
 */
#include <dlfcn.h>
#include <rime_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char** argv) {
  if (argc < 5) {
    fprintf(stderr, "usage: %s SHARED_DIR USER_DIR SCHEMA KEYS [option=0|1 ...]\n", argv[0]);
    return 2;
  }
  const char* plugin = getenv("RIME_PROBE_LUA_PLUGIN");
  static const char* modules[] = {"default", "lua", NULL};
  if (plugin && !dlopen(plugin, RTLD_NOW | RTLD_GLOBAL)) {
    fprintf(stderr, "cannot load %s: %s\n", plugin, dlerror());
    return 1;
  }
  RimeApi* api = rime_get_api();
  RIME_STRUCT(RimeTraits, traits);
  traits.shared_data_dir = argv[1];
  traits.user_data_dir = argv[2];
  traits.prebuilt_data_dir = argv[1];
  traits.staging_dir = NULL;
  traits.distribution_name = "rime-gloss-e2e";
  traits.distribution_code_name = "rime-gloss-e2e";
  traits.distribution_version = "0";
  traits.app_name = "rime.rime-gloss-e2e";
  traits.min_log_level = 2; /* errors only */
  if (plugin) traits.modules = modules;
  api->setup(&traits);
  api->initialize(&traits);
  if (api->start_maintenance(True)) api->join_maintenance_thread();

  RimeSessionId session = api->create_session();
  if (!session) {
    fprintf(stderr, "no session\n");
    return 1;
  }
  if (!api->select_schema(session, argv[3])) {
    fprintf(stderr, "cannot select schema %s\n", argv[3]);
    return 1;
  }
  for (int i = 5; i < argc; i++) {
    char* eq = strchr(argv[i], '=');
    if (!eq) continue;
    *eq = '\0';
    api->set_option(session, argv[i], eq[1] == '1');
  }
  if (!api->simulate_key_sequence(session, argv[4])) {
    fprintf(stderr, "key sequence rejected\n");
    return 1;
  }
  RIME_STRUCT(RimeContext, ctx);
  if (!api->get_context(session, &ctx)) {
    fprintf(stderr, "no context\n");
    return 1;
  }
  for (int i = 0; i < ctx.menu.num_candidates; i++) {
    const RimeCandidate* c = &ctx.menu.candidates[i];
    printf("%s\t%s\n", c->text, c->comment ? c->comment : "");
  }
  api->free_context(&ctx);
  api->destroy_session(session);
  api->finalize();
  return 0;
}
