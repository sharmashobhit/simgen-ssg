### What is simgen-ssg?

`simgen-ssg` is a content recommendation engine tailored specifically for static sites. By leveraging vector search technology, it enables seamless integration of personalized 'you might also like' sections for your blog, FAQs, and various content-driven pages.

### Why simgen-ssg?

- Personalization: Tailor suggestions for a user-centric experience.
- Ease of Integration: Effortlessly implement recommendations into static sites.
- Engagement Boost: Enrich user experiences and increase engagement.

### Who is it for?

- **Bloggers**: Offer personalized 'you might also like' sections for blog posts, keeping readers engaged and on your site longer.
- **Knowledge Base Enhancement**: Implement 'similar articles' suggestions in FAQs or documentation pages, aiding users in finding relevant information quickly.
- **Content Publishing Platforms**: Enhance content discovery by suggesting related articles or posts, keeping users engaged and extending their browsing time.
- **Portfolio Websites**: Showcase similar projects or works to visitors, allowing them to explore related content based on their interests.
- **Educational Websites**: Offer 'you might also like' sections for courses or resources, aiding learners in discovering supplementary material.
- **Community Forums**: Facilitate the discovery of related threads or discussions, encouraging deeper engagement among users.
- **Event or Conference Websites**: Recommend similar events or sessions based on attendee preferences, optimizing their experience and participation.
- **Recipe or Lifestyle Blogs**: Suggest similar recipes or articles catering to specific user tastes or interests.
- **Job Boards**: Offer job recommendations based on user profiles or previous job searches, enhancing user experience and increasing the likelihood of finding suitable positions.
- **Travel Websites**: Recommend similar destinations, accommodations, or activities, making trip planning more personalized and engaging.

## How does it work?

The project uses Qdrant vector database along with [fastembed](https://qdrant.github.io/fastembed/) under the hood to generate vector embeddings for the chunks in your site. It then provides an API to query the vector embeddings across the database to generate related content recommendations.

## How do I use it?

### Installation

#### Dev environment

1. Install the package using `pip install simgen-ssg`
2. Run the server using `simgen-ssg
