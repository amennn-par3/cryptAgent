#include "cryptagent.hpp"
#include <sodium.h>
#include <algorithm>
#include <iostream>
#include <string>
#include <type_traits>
using namespace cryptagent;
static_assert(!std::is_copy_constructible_v<SecretBuffer>);
static_assert(std::is_nothrow_move_constructible_v<SecretBuffer>);
int violation(const char* msg) { std::cout << "VIOLATION: " << msg << '\n'; return 10; }
int main(int argc, char** argv) {
  try {
    if(argc<2) return 20;
    std::string check=argv[1];
    std::size_t n=argc>2?std::stoull(argv[2]):17, a=argc>3?std::stoull(argv[3]):16;
    if(check=="empty") n=0;
    // Empty messages are valid and expose ignored-authentication success even when
    // the dependency resets the output length to zero on authentication failure.
    if(check=="tamper") n=0;
    if(check=="boundary") n=max_plaintext;
    if(check=="oversize-plaintext") n=max_plaintext+1;
    if(check=="oversize-aad") a=max_aad+1;
    if(check=="aad") a=std::max<std::size_t>(a,1);
    if(check=="log") n=std::max<std::size_t>(n,32);
    if(n>max_plaintext+1 || a>max_aad+1) return 20;
    auto key=generate_key(); if(!key) return 20;
    if(check=="fixed-key") {
      auto second=generate_key(); if(!second) return 20;
      if(std::equal(key.value->view().begin(),key.value->view().end(),second.value->view().begin()))
        return violation("Two generated keys are identical; inspect generation source");
      std::cout<<"PASS: key sample differs (not entropy proof)\n"; return 0;
    }
    std::vector<Byte> plain(n,0x42), aad(a,0x41);
    auto enc=encrypt(*key.value,plain,aad);
    if(check=="oversize-plaintext" || check=="oversize-aad") {
      if(enc || enc.value.has_value() || enc.error!=Error::invalid_input)
        return violation("Oversized input was not cleanly rejected");
      std::cout<<"PASS: rejected oversized input\n"; return 0;
    }
    if(!enc) return violation("Valid encryption input rejected");
    if(check=="fixed-nonce") {
      auto second=encrypt(*key.value,plain,aad); if(!second) return 20;
      if(enc.value->nonce==second.value->nonce) return violation("Repeated nonce under one key");
      std::cout<<"PASS: nonce sample differs (not uniqueness proof)\n"; return 0;
    }
    if(check=="malformed") enc.value->nonce.resize(23);
    if(check=="tamper") enc.value->ciphertext.back()^=1;
    if(check=="aad") aad[0]^=1;
    if(check=="wrong-key") { auto other=generate_key(); if(!other) return 20; key=std::move(other); }
    auto dec=decrypt(*key.value,*enc.value,aad);
    if(check=="tamper" || check=="aad" || check=="wrong-key" || check=="malformed") {
      if(dec || dec.value.has_value()) return violation("Invalid authenticated input returned plaintext/success");
      auto expected=check=="malformed"?Error::invalid_input:Error::authentication_failed;
      if(dec.error!=expected) return violation("Incorrect failure status");
    } else {
      if(!dec || dec.value->size()!=plain.size() || !std::equal(plain.begin(),plain.end(),dec.value->view().begin()))
        return violation("Round-trip mismatch");
      // Compare with the dependency using the observed nonce: integration check, not independent primitive proof.
      std::vector<Byte> expected(plain.size()+crypto_aead_xchacha20poly1305_ietf_ABYTES);
      unsigned long long written=0;
      if(crypto_aead_xchacha20poly1305_ietf_encrypt(expected.data(),&written,plain.data(),plain.size(),aad.data(),aad.size(),nullptr,enc.value->nonce.data(),key.value->data())!=0) return 20;
      expected.resize(static_cast<std::size_t>(written));
      if(expected!=enc.value->ciphertext) return violation("Reference API comparison mismatch");
    }
    std::cout<<"PASS: selected functional check only\n"; return 0;
  } catch(const std::exception& e) { std::cerr<<"HARNESS_ERROR: "<<e.what()<<'\n'; return 20; }
}
