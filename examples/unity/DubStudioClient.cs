// Unity: put on a GameObject with an AudioSource, then
// StartCoroutine(GetComponent<DubStudioClient>().Speak("ข้อความ", "giant", "angry", "cave"));
// Requires Dub Studio running (start.bat / start.sh) on the same computer.
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class DubStudioClient : MonoBehaviour
{
    public string baseUrl = "http://127.0.0.1:8000";

    [System.Serializable]
    class SpeakRequest { public string text, character, mood, atmosphere; }

    public IEnumerator Speak(string text, string character = "me", string mood = "normal", string atmosphere = "none")
    {
        var json = JsonUtility.ToJson(new SpeakRequest { text = text, character = character, mood = mood, atmosphere = atmosphere });
        using var req = new UnityWebRequest(baseUrl + "/api/v1/speak", "POST");
        req.uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(json));
        req.downloadHandler = new DownloadHandlerAudioClip(baseUrl + "/api/v1/speak", AudioType.WAV);
        req.SetRequestHeader("Content-Type", "application/json");
        yield return req.SendWebRequest();
        if (req.result != UnityWebRequest.Result.Success) { Debug.LogError("Dub Studio: " + req.error); yield break; }
        var source = GetComponent<AudioSource>();
        source.clip = DownloadHandlerAudioClip.GetContent(req);
        source.Play();
    }
}
