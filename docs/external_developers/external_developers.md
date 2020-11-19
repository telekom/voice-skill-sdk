# Developer Platform (external document for 3rd party developers)

## Notes

*  This is the content to be used by the Developer Portal/Platform being developed by the Hub:raum team. The red highlighted text need better wording/review of the sub-section. Please feel free to edit or comment (inline or page comments) for any feedback.

* In the long term, how does the account management of external developers work? Where do we maintain their information and accounts? How is that mapped with the various tools and systems that we have? o One place could be developer.telekom.com. IBS is another tool however, that is not meant for such a developer community that we want to create


* Notes

* Getting Started

* Voice Platform as a Service (VPaaS)

	* Building skills for Magenta Speakers

		* Voice Chain

		* Terminologies

			* Skills

			* Common Voice Interface (CVI)

			* Intents

			* Skill Domains

			* Entities

			* Hybrid Skill

			* Context

			* Responses

		* Skill Lifecycle

		* Skill Provider Registration

			* Getting your companion app (user) nickname from the Hallo Magenta App

		* Initial Skill Creation

			* Prerequisites

		* Skill Development

			* Magenta Voice Skill Software Development Kit (Skill SDK)

			* Testing the skill locally

			* CLI Testing

			* Server-less Deployment (AWS & Azure)

			* Configuring Skill on SDP

				* Adding a Skill Tester to your skill on SDP

				* Configuring the skill parameters in development environment

				* Adding a Catalogue to your Skill for the companion app

			* Further Information

		* Skill Publishing

		* Skill Deletion

	* Integrating voice in mobile application using Mobile SDK

	* Enabling voice technology assistants on devices using Device SDK

	* Developing enterprise solutions using B2B use-cases from Voice Platform

	* Extending VPaaS

* Voice Application

	* B2C Solutions

	* B2B(2C) Solution


## Getting Started

We understand Voice as a key enabler for seamless processes, personalised experiences and conversational AI solutions for companies and their consumers.

Telekom Voicification Suite is a combined offering of:

1. Voice Platform as a Service (VPaaS)

2. Various Voice Applications build on top of the platform that can be used with multiple touch points like Magenta Smart Speakers, Magenta TV, voice integrated mobile apps, etc., and

3. Last but not the least the enablement services offered to help build voice empowered applications and integrate voice technology in custom B2C and B2B solutions.



The picture below shows the overall offered components, applications, services offered as part of Telekom Voicification Suite. Most of the components and services are customizable and can be used with or without other provided services.

![Fig.1](./external_developers_0.png)


Give a flow on how the Voice applications relate to the Voice Platform before starting the next section

## Voice Platform as a Service (VPaaS)

Magenta Voice Platform is a technical platform that enables flexible processing of voice interactions. It consists of tools used for the development of Voice Applications both for B2C (Business to Consumer) and B2B (Business to Business) customers:

1. Basic services like Cloud Infrastructure to host and deploy your applications in containers, Common Voice Interface that is the heart of the Voicification suite orchestrating the invocation of various tasks being performed at the application layer, and
2. Additional intelligent services like natural language understanding components, automated speech recognizer, smart voice orchestrator called the Common Voice Interface, etc.
3. The software development kits that provide you with the way to build custom applications on top of the platform and integrate existing applications or touch points with voice technology.

The voice platform is provided as a service to its consumers. Using VPaaS, you can:

- Build voice skills (capabilities) for the touch points like Magenta Speakers
- Integrate voice to your applications
- Enable voice in your devices
- Develop innovative enterprise solutions
- Extend Telekom Voicification Suite itself by adding custom bots/applications in the Applications Catalog

### Building skills for Magenta Speakers
**Voice Chain**
To understand how the flow of your command works, let's go through an overview of what happens when you give a command to the Magenta Voice assistant. Below is an example of a weather 'skill':

- You speak "Hallo Magenta, Wie ist das Wetter heute in Mannheim?" to the Magenta Speaker.
- Magenta Smart Speaker listens to the phrase "Hallo Magenta" and starts sending your command to the Speech Recognizer in the cloud (Voice Platform).
- The Automatic Speech Recognizer (ASR) using the Machine Learning tools sends its output to the Natural Language Understanding (NLU) component.
- The NLU determines which skill domain and skill does the command belong to and forwards it to that specific skill - in this example, it is the weather skill implemented as part of the global skill domain WEATHER.
- The weather skill queries a backend weather forecasting service with the entities "today" and "Mannheim".
- The result is converted in a suitable response type by the Voice Platform and sent back to you - in this example, voice answer by Magenta Assistant and Text link (weather forecast of Mannheim) to the Hallo Magenta mobile app.

The diagram below shows the interaction:

![Fig.2](./external_developers_1.png)

It is also important to understand a few terminologies before you can jump onto creating a skill. 
### Terminologies
**Skills**

Skills are a set of (intelligent) capabilities that make the voice assistant smart. For example, you can ask the voice assistant to call your mobile contacts or set an alarm (speakers as touch point), or switch on the Magenta TV (set top boxes, remote controlled units as touch points). Technically, it is a service which is called by the Voice Platform in order to perform some business logic. A Skill is part of (or a building block of) a Voice Application.

**Common Voice Interface (CVI)**

Name of the central component of the Voice Platform. It is the entry point for the backend for all commands in natural language and helps in orchestrating the voice flow between various platform components (ASR, NLU, TTS) and calling the appropriate skills via REST APIs. It also manages the dialog with the user by keeping a track of the 'Context' and enrich with the user data.

**Intents**

An Intent is a core action that the user means when speaking in Natural Language. It represents a task or action the user wants to perform.

An 'intent' triggers a 'skill' call in the Voice Platform. 

**Skill Domains**

The Skill Domains are constructed to encapsulate multiple skills serving the same tasks, and supporting the same intents. The domain to skill relation is 1:n where one of the skills is set as default.

In programming lingo, Domains are abstract skills and skills are implementation of domains. A user can use the favourite skill implementation for the skill domain.

**Entities**

Important words in the user command relevant to an intent - 'parameters' to the skill. For eg.

"What's the weather tomorrow in Berlin?"

The Voice Platform will identify one intent (get the weather) and two entities:

* a time parameter - with the value "tomorrow"
* a location parameter - with the value "Berlin"

You can read more about entities [here](https://smarthub-wbench.wesp.telekom.net/gitlab/smarthub_skills/skill_sdk_python/-/blob/master/docs/entities.md) 

**Hybrid Skill**

A hybrid skill is a type of skill which requires a local plugin (also called as "local kit") to be deployed on a touch point to work. For example:

* the Deezer bot requires a local Deezer plugin running on the speaker, to manage the Deezer DRM.
* the DECT skill requires a local plugin on the Magenta smart speaker to pilot the DECT chipset of the speaker.

### Kits related information
**Context**

Skill invocation request consists of two data transfer object (DTO): a request context and request session. The context carries data about an intent being invoked (intent name, attributes, tokens, etc), while the session carries data that persists between user interactions.

Before calling an intent handler function, SDK injects the context object into the global address space. Global context object is importable from smarthub_sdk.intents module (this is a thread-safe instance referring to currently running request's context):

```
>>> from smarthub_sdk.intents import context
>>> context
<smarthub_sdk.intents.LocalContext object at 0x7faa1bc75910>
```

You can read more about context [here](https://smarthub-wbench.wesp.telekom.net/gitlab/smarthub_skills/skill_sdk_python/-/blob/master/docs/context.md)

**Responses**

Any valid call of an intent handler may return Response type object. If a call of the intent is valid, the requested user action processed as intended. Furthermore, it covers any exception from the normal processing that is handled by notifying the client/user about the result. In other words: Everything that is not an unrecoverable error.

You can read more about responses [here](https://smarthub-wbench.wesp.telekom.net/gitlab/smarthub_skills/skill_sdk_python/-/blob/master/docs/response.md)

**Skill Lifecycle**

Let's jump right into the implementation and configuration of a skill.

The lifecycle of developing a skill and integrating (configuring) the skill in the voice chain is divided in 5 phases:

* Skill Provider Registration
	* Inviting users as Skill Providers on Skill Development Portal (SDP) to create new skills in the tool under existing domains.
* Skill Initiation
	* Inviting users as Skill Developers for skills (on SDP) and their configurations created by Skill Providers. Skill configuration can be changed and managed by Skill Developers after this step.
* Skill Development
	* Implementing a skill as a micro-service, deploying it as a web application and testing it end to end using the voice assistant
* Skill Publishing
	* Bringing the skill to production for all the users
* Skill Deletion
        * Deleting skill configurations from SDP

A detailed overview of the above steps is shown in the pic below:


Give a flow on how the Voice applications relate to the Voice Platform before starting the next section

## Voice Platform as a Service (VPaaS)

Magenta Voice Platform is a technical platform that enables flexible processing of voice interactions. It consists of tools used for the development of Voice Applications both for B2C (Business to Consumer) and B2B (Business to Business) customers:

1. Basic services like Cloud Infrastructure to host and deploy your applications in containers, Common Voice Interface that is the heart of the Voicification suite orchestrating the invocation of various tasks being performed at the application layer, and
2. Additional intelligent services like natural language understanding components, automated speech recognizer, smart voice orchestrator called the Common Voice Interface, etc.
3. The software development kits that provide you with the way to build custom applications on top of the platform and integrate existing applications or touch points with voice technology.

The voice platform is provided as a service to its consumers. Using VPaaS, you can:

- Build voice skills (capabilities) for the touch points like Magenta Speakers
- Integrate voice to your applications
- Enable voice in your devices
- Develop innovative enterprise solutions
- Extend Telekom Voicification Suite itself by adding custom bots/applications in the Applications Catalog

### Building skills for Magenta Speakers
**Voice Chain**
To understand how the flow of your command works, let's go through an overview of what happens when you give a command to the Magenta Voice assistant. Below is an example of a weather 'skill':

- You speak "Hallo Magenta, Wie ist das Wetter heute in Mannheim?" to the Magenta Speaker.
- Magenta Smart Speaker listens to the phrase "Hallo Magenta" and starts sending your command to the Speech Recognizer in the cloud (Voice Platform).
- The Automatic Speech Recognizer (ASR) using the Machine Learning tools sends its output to the Natural Language Understanding (NLU) component.
- The NLU determines which skill domain and skill does the command belong to and forwards it to that specific skill - in this example, it is the weather skill implemented as part of the global skill domain WEATHER.
- The weather skill queries a backend weather forecasting service with the entities "today" and "Mannheim".
- The result is converted in a suitable response type by the Voice Platform and sent back to you - in this example, voice answer by Magenta Assistant and Text link (weather forecast of Mannheim) to the Hallo Magenta mobile app.

The diagram below shows the interaction:

