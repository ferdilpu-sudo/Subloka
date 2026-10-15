#include <whisper.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>
void quiet(enum ggml_log_level, const char *, void *) {}
int main(int argc, char **argv) {
 // Local diagnostic only: model, 16kHz float32 mono PCM, window seconds,
 // output TSV, optional VAD model. Never prints transcript text to logs.
 if(argc < 5 || argc > 6) return 2;
 whisper_log_set(quiet, nullptr);
 auto cp=whisper_context_default_params(); cp.use_gpu=false; cp.flash_attn=false;
 auto *ctx=whisper_init_from_file_with_params(argv[1],cp); if(!ctx) return 3;
 FILE *f=fopen(argv[2],"rb"); if(!f) return 5;
 fseek(f,0,SEEK_END); long bytes=ftell(f); rewind(f);
 if(bytes<=0 || bytes%4 || bytes>600L*16000*4) { fclose(f); return 5; }
 size_t n=bytes/4; std::vector<float> a(n);
 if(fread(a.data(),4,n,f)!=n) { fclose(f); return 5; } fclose(f);
 int seconds=atoi(argv[3]); if(seconds<1 || seconds>30) return 2;
 size_t stride=seconds*16000; FILE *o=fopen(argv[4],"w"); if(!o) return 5;
 size_t begin=0, finish=n;
 for(size_t off=begin;off<finish;off+=stride){
  auto p=whisper_full_default_params(WHISPER_SAMPLING_BEAM_SEARCH);
  p.n_threads=4; p.language="id"; p.translate=false; p.no_context=true;p.no_timestamps=false;
  p.print_realtime=p.print_progress=p.print_timestamps=p.print_special=false; p.suppress_nst=true;
  if(argc==6) { p.vad=true; p.vad_model_path=argv[5]; }
  int len=std::min(stride,finish-off);
  if(whisper_full(ctx,p,a.data()+off,len)!=0) return 4;
  int ns=whisper_full_n_segments(ctx);
  for(int i=0;i<ns;i++) fprintf(o,"%zu\t%lld\t%lld\t%s\n",off/16000,
    (long long)whisper_full_get_segment_t0(ctx,i)*10000,
    (long long)whisper_full_get_segment_t1(ctx,i)*10000,whisper_full_get_segment_text(ctx,i));
  fflush(o); fprintf(stderr,"finished window %zu, segments %d\n",off/16000,ns);
 }
 fclose(o);whisper_free(ctx);
}
