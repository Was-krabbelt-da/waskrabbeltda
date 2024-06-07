<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/Was-krabbelt-da/waskrabbeltda">
    <img src="assets/logo.png" alt="Logo" width="400" height="200">
  </a>

<h3 align="center">Was krabbelt da ?</h3>

  <p align="center">
    Was krabbelt da provides journalistic tools to report on the biodiversity in your area. Based on a DIY camera trap, developed by <a href="https://github.com/maxsitt">Maximilian Sittinger</a>, this project provides a platform to automatically receive and classify the images, as well as, a dashboard to visualize and analyze the data.
    <br />
    <a href="https://github.com/Was-krabbelt-da/waskrabbeltda?tab=readme-ov-file#getting-started"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <!-- <a href="https://github.com/Was-krabbelt-da/waskrabbeltda">View Demo</a>
    · -->
    <a href="https://github.com/Was-krabbelt-da/waskrabbeltda/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/Was-krabbelt-da/waskrabbeltda/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    <li><a href="#deployment">Deployment</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#technical-details">Technical Details</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

Use this repository to setup your own API and dashboard for the insect-detect camera trap.
The API provides endpoints to classify images and store the classification data and images. The classification and image data can then be accessed via various data endpoints.
The Dashboard provides a user interface to explore classified image data, visualize the data and download the collected data.
![Dashboard Screenshot][product-screenshot]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With

* [![FastAPI][FastAPI]][Fastapi-url]
* [![Streamlit][Streamlit]][Streamlit-url]

### Based on

* [Streamlit FastAPI Model Serving](https://github.com/davidefiocco/streamlit-fastapi-model-serving) by [Davide Fiocco](https://davidefiocco.github.io)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

### Prerequisites

For local development, you need to have the following installed:

* Docker: https://docs.docker.com/get-docker/

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/Was-krabbelt-da/waskrabbeltda
   ```
2. Create an API key e.g. by running the following in your command line:
    ```sh
    openssl rand -base64 128 | tr -d '\n' | pbcopy
    ```
3. Create a `.env` file in the `fastapi` folder (e.g. by copying or renaming the `.env.example` file) and fill in the created API key value. 
   ```sh
   API_KEY=
   ```
4. Create a `.env` file in the `streamlit` folder (e.g. by copying or renaming the `.env.example` file) and fill in the created API key value. You can also add a name for the camera trap which will be displayed in the dashboard and used for downloadable files. The `DATA_ENDPOINT` should be the URL of the FastAPI service, in the case of a local setup with no changes to the docker-compose file, it should be `http://fastapi:8000`.
   ```sh .env
   API_KEY=
   CAMERA_NAME=
   DATA_ENDPOINT="http://fastapi:8000"
   ```
5. Build the project with docker-compose
   ```sh
   docker compose build
   ```
6. Start the project with docker-compose
   ```sh
    docker compose up
    ```
7. Visit the FastAPI documentation of the resulting service at http://localhost:8000/docs with a web browser.
8. Visit the streamlit UI at http://localhost:8501.

You should be able to see an empty dashboard with no data (currently the dashboard displays an error if it is completely empty, send a request with mock data to the API to resolve this an be able to fix it). You can fill it by sending requests to the endpoints specified in the FastAPI documentation at http://localhost:8000/docs.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- Usage -->
## Usage

The endpoints of the FastAPI service are documented in the FastAPI documentation at http://localhost:8000/docs. 
Send requests to the `/classify` endpoint to classify images and store the classification data and images. The classification and image data can then be accessed via various data endpoints.
E.g. you can query all currently stored classifications with a GET request to the `/data/classification` endpoint.

The Streamlit UI provides a user interface to explore classified image data, automatically visualizes the data, shows images of the last captured insects, allows exploring all captured tracking runs and downloading the collected data. The UI is accessible at http://localhost:8501 or the respective URL of the deployed service.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
<!-- Deployment -->
## Deployment
The project is setup to be deployed via two fly machines with a volume attached to the FastAPI machine for persistence.
[fly.io](https://fly.io) is a platform that allows you to deploy your container-based applications with as little overhead as possible.

### Prerequisites
- A fly.io account and the flyctl CLI installed, which you can obtain [here](https://fly.io/docs/hands-on/).
  
### Deployment Steps
- The WasKrabbeltDa project is setup in two services, a FastAPI service and a Streamlit service, corresponding to the two folders in the repository.
- Each service has its own `Dockerfile` and `fly.toml` and can/has to be deployed independently.
  - (`fly.toml` files configure the deployment settings for the fly.io platform)
  
- For a full deployment:
- 
**1. Deploy the FastAPI service**
    - Change into the `fastapi` folder and deploy the service for the first time with the following command:
      ```sh
      cd fastapi
      fly launch
      ```
    - Follow the instructions in the terminal to configure the deployment.
    - After the deployment is finished, you can set the API key as a secret with the following command:
      ```sh
      fly secrets set API_KEY=...
      ```
    - The deployment should automatically included an attached volume for persistence. See the technical details for more information.
  
**2. Deploy the Streamlit service**
    - Change into the `streamlit` folder and deploy the service for the first time with the following command:
      ```sh
      cd streamlit
      fly launch
      ```
    - Follow the instructions in the terminal to configure the deployment.
    - After the deployment is finished, you can set the API key and the data endpoint as secrets with the following command:
      ```sh
      fly secrets set API_KEY=... DATA_ENDPOINT=...
      ```
    - Data endpoint should be the URL of the FastAPI service, e.g. `https://fastapi-1234.fly.dev`.
1. After the deployment of both services, you can visit the Streamlit UI at the URL provided by the Streamlit service deployment.
2. For further deployment steps it's sufficient to run `fly deploy` in the respective folder of the service you want to update.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- Technical Details -->
## Technical Details

### Persistence
The current persistence for data works with a volume attached to the FastAPI server. The classification data is stored in a CSV, that gets read and written to on every request. Fly.io keeps snapshots of the last five days of the volume, which is the current backup strategy. 
This approach is sufficient and time-efficient for the prototype phase, but should be replaced with a more robust solution featuring a database in case of further development. 
To ensure data consistency with this approach we need to ensure that only one request is handled at a time. See 'Synchronicity' for more details.
To manage the volume size an auto-extend strategy is used. See 'Storage space' for more details.

### Synchronicity
To ensure data consistency (as explained in the **Persistence** section) we need to ensure that only one request is handled at a time. This is achieved by limiting the FastAPI instances to exactly one and by locking the classify endpoint to only allow one request at a time.

In the fly.toml file of the FastAPI service, the following settings are used to achieve exactly one machine running at all times:
```toml
  min_machines_running = 1
  max_machines_running = 1
```

To lock the classify endpoint, the classify endpoint acquires a lock before processing the request and releases it after the request is processed.

### Storage space
Currently, the volume is set to 1GB and will auto-extend up until 3GB if needed (at an 80% capacity threshold). 3GB is the current limit of total free provisioned storage capacity on fly.io per organization. Depending on the expected storage requirements, this limit might need to be adjusted.
As the stored images are small cropped versions of the original images, the storage requirements are expected to be low and the 1GB volume proved sufficient in our trial runs.



<!-- LICENSE -->
## License
This repository is distributed under the MIT License with one exception: The subdirectory `fastapi` is distributed under the GPL3 License.

See the respective `LICENSE.txt` files for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->
## Contact

**Development:**
Theresa Hradilak - theresa.hradilak@gmail.com

**Content/Journalistic Inquiries:**
Joachim Budde - [@Joachim Budde](https://www.linkedin.com/in/joachim-budde-3296822b0/) - https://www.joachimbudde.de - ich@joachimbudde.de

**Project Webpage:** [https://waskrabbeltda.de](https://waskrabbeltda.de)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [**Maximilian Sittinger**](https://github.com/maxsitt) for developing the [insect-detect camera trap](https://github.com/maxsitt/insect-detect), making it available as an open-source project and documenting it extensively [here](https://maxsitt.github.io/insect-detect-docs/), which made this project possible in the first place. And for the great support for this project.
* [**Davide Fiocco**](https://github.com/davidefiocco) for the [Streamlit FastAPI Model Serving](https://github.com/davidefiocco/streamlit-fastapi-model-serving) template that made the setup of this project a enjoyable efficient experience.
* [**Othneil Drew**](https://github.com/othneildrew) for the actual [best README template](https://github.com/othneildrew/Best-README-Template).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/Was-krabbelt-da/waskrabbeltda.svg?style=for-the-badge
[contributors-url]: https://github.com/Was-krabbelt-da/waskrabbeltda/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Was-krabbelt-da/waskrabbeltda.svg?style=for-the-badge
[forks-url]: https://github.com/Was-krabbelt-da/waskrabbeltda/network/members
[stars-shield]: https://img.shields.io/github/stars/Was-krabbelt-da/waskrabbeltda.svg?style=for-the-badge
[stars-url]: https://github.com/Was-krabbelt-da/waskrabbeltda/stargazers
[issues-shield]: https://img.shields.io/github/issues/Was-krabbelt-da/waskrabbeltda.svg?style=for-the-badge
[issues-url]: https://github.com/Was-krabbelt-da/waskrabbeltda/issues
[license-shield]: https://img.shields.io/github/license/Was-krabbelt-da/waskrabbeltda.svg?style=for-the-badge
[license-url]: https://github.com/Was-krabbelt-da/waskrabbeltda/blob/main/LICENSE.txt
[product-screenshot]: assets/screenshot.png
[FastAPI]: https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi
[Fastapi-url]: https://fastapi.tiangolo.com
[Streamlit]: https://img.shields.io/badge/-Streamlit-61DAFB?style=plastic&logo=streamlit
[Streamlit-url]: https://streamlit.io