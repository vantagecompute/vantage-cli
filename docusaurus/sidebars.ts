import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  // Manually curated sidebar for Vantage CLI documentation
  tutorialSidebar: [
    'index', // Homepage/Overview
    {
      type: 'category',
      label: 'Getting Started',
      items: [
        'installation',
        'usage',
        'private-vantage-installation',
        'deployment-applications/index',
        'notebooks',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'commands',
        'architecture',
      ],
    },
    {
      type: 'category',
      label: 'Support',
      items: [
        'troubleshooting',
        'contact',
        'contributing',
      ],
    },
  ],
};

export default sidebars;
