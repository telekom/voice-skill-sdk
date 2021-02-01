# Client Kits

In a voice skill context, *kit* represents a tenant-specific business logic on the client.
To activate a client kit, you have to attach a corresponding command to the response object.

For example to play a stream from a URL, add `AudioPlayer.play_stream` command:

```python
from skill_sdk.responses import tell, AudioPlayer

response = tell('Here is a massive stream from London!').with_command(
    AudioPlayer.play_stream('http://uk1-pn.mixstream.net/8698.m3u'))
```


The following kit *types* are currently supported:

* `audio_player`
* `calendar`
* `system`
* `timer`

## Audio Player

This kit handles audio player/radio functions.

### Actions

Supported actions:

- `AudioPlayer.play_stream(url: str)`: start playing a generic internet stream, specified by "url" parameter.
  

- `AudioPlayer.play_stream_before_text(url: str)`: start playing a stream, before pronouncing the response.
  

- `AudioPlayer.stop(content_type: ContentType = None, text: str = None)`: stop currently playing media 
  (voicemail, radio, content tts), optionally pronounce text **before** stopping.


- `AudioPlayer.pause(content_type: ContentType = None, text: str = None)`: pause playback, 
  optionally pronounce text **after** playback paused


- `AudioPlayer.resume(content_type: ContentType = None)`: resume paused media, say response text **before** resuming

### Samples

```python
from skill_sdk import tell, intent_handler
from skill_sdk.responses import AudioPlayer

KOOL_STREAM = 'http://uk1-pn.mixstream.net/8698.m3u'

@intent_handler('INTENT__PLAY')
def play():
    """Intent activated when user says 'Play'"""
    return tell('Here is a massive stream from London!').with_command(
        AudioPlayer.play_stream(KOOL_STREAM))

@intent_handler('INTENT__STOP')
def stop():
    """Intent activated when user says 'Stop'"""
    return tell('Bye!').with_command(
        AudioPlayer.stop('Stopping kool stream...'))

@intent_handler('INTENT__PAUSE')
def pause():
    """Intent activated when user says 'Pause'"""
    return tell('Pausing kool stream...').with_command(
        AudioPlayer.pause('Playback paused. To resume, say "resume".'))

@intent_handler('INTENT__RESUME')
def resume():
    """Intent activated when user says 'Continue'"""
    return tell('Resuming kool stream...').with_command(
        AudioPlayer.resume())
```

## Calendar

Calendar kit can either snooze a calendar alarm or cancel previously set snooze.

### Actions

Supported actions:

- `Calendar.snooze_start(snooze_seconds: int = None)`: snooze calendar alarm by number of seconds specified as parameter.
  

- `Calendar.snooze_cancel()`: cancel current snooze.
 

### Samples

```python
from skill_sdk import tell, intent_handler
from skill_sdk.responses import Calendar

@intent_handler('INTENT__SNOOZE')
def snooze(time: int = None):
    """Intent activated when user says 'Snooze 5 minutes'

    @param time: snooze time in minutes
    """
    seconds = time * 60 
    return tell('Sleep well another %s seconds', seconds).with_command(
        Calendar.snooze_start(seconds))
```

## System 

System functions kit.

### Actions

- `System.stop(skill_type: SkillType = None)`: Send a `Stop` event: stops a foreground activity on the device. 
  If there was another activity in background, it will gain focus.
  `skill_type` parameter can be one of `System.SkillType` values: `System.SkillType.TIMER`/`CONVERSATION`/`MEDIA`
  It can specify a skill-related activity to stop. If no `skill_type` specified, all activities are stopped.
  

- `System.pause()`: pause currently active content (if supported).


- `System.resume()`: resume media (if paused).


- `System.next()`: switch to next item in content channel. 


- `System.previous()`: switch to previous item in content channel. 


- `System.say_again()`: repeat last uttered sentence (from the dialog channel). 


- `System.volume_up()`: increase the volume one notch.


- `System.volume_down()`: decrease the volume one notch.


- `System.volume_to(value: int = 0)`: set the volume to an absolute value (0-10).


### Samples

```python
from skill_sdk import tell, intent_handler
from skill_sdk.responses import System

@intent_handler('VOLUME__UP')
def volume_up():
    """Intent activated when user says 'Make it louder'"""
    return tell('Volume up.').with_command(
        System.volume_up())

@intent_handler('VOLUME__DOWN')
def volume_down():
    """Intent activated when user says 'Make it quieter'"""
    return tell('Volume down.').with_command(
        System.volume_down())

@intent_handler('GLOBAL__STOP')
def stop():
    """Intent activated when user says 'Stop!'"""
    return tell('Stopped.').with_command(
        System.stop())
```


## Timer

Timer kit: start and stop Timer/Reminder/Alarm animation.
The animation is a combination of blinking pink round LED and repeating blipping sound on a device.

Used by a timer skill to announce the end of a timer, or by calendar skill to fire up a reminder/alarm.

### Actions

- `Timer.set_timer()`: fire up a "timer" animation. 
  After animation started, it keeps running for max. 10 min if no user interaction happens.


- `Timer.cancel_timer()`: cancel currently running animation.



### Samples

```python
from skill_sdk import tell, intent_handler
from skill_sdk.responses import Timer

@intent_handler('TIMER__START')
def start():
    """Intent activated by an external reminder service"""
    return tell('Here is your reminder!').with_command(
        Timer.set_timer())

@intent_handler('TIMER__STOP')
def stop():
    """Intent activated when user says 'Stop!'"""
    return tell().with_command(
        Timer.cancel_timer())
```
