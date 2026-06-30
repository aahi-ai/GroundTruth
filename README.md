<img width="884" height="214" alt="Screenshot 2026-06-30 at 2 01 35 PM" src="https://github.com/user-attachments/assets/eacdac7c-9a93-407a-9542-8b26da74c07e" />

# GroundTruth

GroundTruth is a crop health tool to analyze plant and crop vegetation using satellite imagery and AI-Powered photo scanning.

**Try it live: [groundtruth-rust.vercel.app](https://groundtruth-rust.vercel.app/)**

## What is this?

Two independent tools in one app. The Satellite tool lets you draw any field boundary on a map and pulls the latest cloud-free Sentinel-2 satellite pass over that exact shape, turning raw vegetation data (NDVI) into a zone-by-zone health heatmap and a 0–100 health score. The Photo tool lets you upload a close-up shot of a plant or leaf and runs it through a vision AI model, flagging visible signs of stress like discoloration, wilting, or pest damage and also returns a 0–100 score. Both tools are fully independent, each gives you a real result on its own.

## Why I built this

On a recent trip to my grandfather's village in India, I took a look at all the fields he'd take care of every day. He'd spend hours each day monitoring and growing all the plants and crops. I created GroundTruth to make monitoring crop and plant health easier and more efficient.

## How to use it

Visit: [groundtruth-rust.vercel.app](https://groundtruth-rust.vercel.app/) | No installation or sign-in required. 

**Satellite tool:**
1. Go to the Satellite tab
2. Search a city or address to navigate the map
3. Use the polygon tool to draw your field boundary
4. Wait ~3-10 seconds while real satellite data is fetched
5. See the NDVI heatmap and health score for your field

**Photo tool:**
1. Go to the Photo tab
2. Click to upload or drag in a close-up plant/leaf photo
3. Wait a few seconds for the AI scan
4. See the health score, summary, and any detected issues

## Tech Stack

**Frontend:** HTML / CSS / JavaScript

**Backend:** Python / FastAPI

**Satellite data:** Microsoft Planetary Computer 

**Photo analysis:** OpenRouter vision API 

— made by aahi
