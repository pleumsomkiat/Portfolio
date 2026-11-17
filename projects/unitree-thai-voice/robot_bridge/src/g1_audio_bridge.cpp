#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include <unitree/common/time/time_tool.hpp>
#include <unitree/robot/channel/channel_factory.hpp>
#include <unitree/robot/g1/audio/g1_audio_client.hpp>

namespace {

constexpr std::size_t kChunkBytes = 96'000;  // 3 seconds of 16 kHz, mono, s16le.
constexpr const char* kAppName = "g1_thai_chatbot";

struct WavData {
  std::vector<uint8_t> pcm;
  uint16_t channels = 0;
  uint16_t bits_per_sample = 0;
  uint32_t sample_rate = 0;
  uint16_t audio_format = 0;
};

uint16_t ReadU16(std::istream& input) {
  uint8_t bytes[2];
  input.read(reinterpret_cast<char*>(bytes), sizeof(bytes));
  return static_cast<uint16_t>(bytes[0] | (bytes[1] << 8));
}

uint32_t ReadU32(std::istream& input) {
  uint8_t bytes[4];
  input.read(reinterpret_cast<char*>(bytes), sizeof(bytes));
  return static_cast<uint32_t>(bytes[0] | (bytes[1] << 8) | (bytes[2] << 16) |
                               (bytes[3] << 24));
}

bool ReadWav(const std::string& filename, WavData* result, std::string* error) {
  std::ifstream input(filename, std::ios::binary);
  if (!input) {
    *error = "Cannot open WAV: " + filename;
    return false;
  }
  char riff[4], wave[4];
  input.read(riff, 4);
  (void)ReadU32(input);
  input.read(wave, 4);
  if (!input || std::memcmp(riff, "RIFF", 4) != 0 || std::memcmp(wave, "WAVE", 4) != 0) {
    *error = "Expected a RIFF/WAVE file";
    return false;
  }

  bool has_fmt = false;
  bool has_data = false;
  while (input && !(has_fmt && has_data)) {
    char chunk_id[4];
    input.read(chunk_id, 4);
    if (!input) break;
    const uint32_t size = ReadU32(input);
    if (!input) break;
    if (std::memcmp(chunk_id, "fmt ", 4) == 0) {
      if (size < 16) {
        *error = "Invalid fmt chunk";
        return false;
      }
      result->audio_format = ReadU16(input);
      result->channels = ReadU16(input);
      result->sample_rate = ReadU32(input);
      (void)ReadU32(input);  // byte rate
      (void)ReadU16(input);  // block align
      result->bits_per_sample = ReadU16(input);
      if (size > 16) input.seekg(static_cast<std::streamoff>(size - 16), std::ios::cur);
      has_fmt = true;
    } else if (std::memcmp(chunk_id, "data", 4) == 0) {
      result->pcm.resize(size);
      input.read(reinterpret_cast<char*>(result->pcm.data()), static_cast<std::streamsize>(size));
      if (!input) {
        *error = "Truncated data chunk";
        return false;
      }
      has_data = true;
    } else {
      input.seekg(static_cast<std::streamoff>(size), std::ios::cur);
    }
    if (size % 2 == 1) input.seekg(1, std::ios::cur);  // RIFF chunks are word aligned.
  }
  if (!has_fmt || !has_data) {
    *error = "WAV needs both fmt and data chunks";
    return false;
  }
  if (result->audio_format != 1 || result->sample_rate != 16000 || result->channels != 1 ||
      result->bits_per_sample != 16) {
    *error = "Expected PCM s16le, 16000 Hz, mono WAV";
    return false;
  }
  return true;
}

void PrintUsage() {
  std::cerr << "Usage:\n"
            << "  g1_audio_bridge --interface <iface> --wav <16k-mono-s16le.wav>\n"
            << "  g1_audio_bridge --interface <iface> --native-text <text> [--speaker-id 0|1]\n";
}

}  // namespace

int main(int argc, char* argv[]) {
  std::string interface_name;
  std::string wav_path;
  std::string native_text;
  int speaker_id = 0;
  for (int index = 1; index < argc; ++index) {
    const std::string arg = argv[index];
    if ((arg == "--interface" || arg == "--wav" || arg == "--native-text" || arg == "--speaker-id") &&
        index + 1 >= argc) {
      PrintUsage();
      return 2;
    }
    if (arg == "--interface") interface_name = argv[++index];
    else if (arg == "--wav") wav_path = argv[++index];
    else if (arg == "--native-text") native_text = argv[++index];
    else if (arg == "--speaker-id") speaker_id = std::stoi(argv[++index]);
    else {
      PrintUsage();
      return 2;
    }
  }

  if (interface_name.empty() || (!wav_path.empty() == !native_text.empty()) || speaker_id < 0 || speaker_id > 1) {
    PrintUsage();
    return 2;
  }

  // Audio only: this program never imports locomotion or motor-control clients.
  unitree::robot::ChannelFactory::Instance()->Init(0, interface_name);
  unitree::robot::g1::AudioClient client;
  client.Init();
  client.SetTimeout(10.0F);

  if (!native_text.empty()) {
    const int32_t code = client.TtsMaker(native_text, speaker_id);
    std::cout << "TtsMaker returned " << code << "\n";
    return code == 0 ? 0 : 1;
  }

  WavData wav;
  std::string error;
  if (!ReadWav(wav_path, &wav, &error)) {
    std::cerr << "WAV validation failed: " << error << "\n";
    return 2;
  }

  const std::string stream_id = std::to_string(unitree::common::GetCurrentTimeMillisecond());
  for (std::size_t offset = 0; offset < wav.pcm.size(); offset += kChunkBytes) {
    const std::size_t bytes = std::min(kChunkBytes, wav.pcm.size() - offset);
    std::vector<uint8_t> chunk(wav.pcm.begin() + static_cast<long>(offset),
                               wav.pcm.begin() + static_cast<long>(offset + bytes));
    const int32_t code = client.PlayStream(kAppName, stream_id, chunk);
    if (code != 0) {
      std::cerr << "PlayStream returned " << code << "\n";
      client.PlayStop(kAppName);
      return 1;
    }
    std::this_thread::sleep_for(std::chrono::seconds(1));
  }
  client.PlayStop(kAppName);
  std::cout << "Audio stream sent successfully\n";
  return 0;
}
