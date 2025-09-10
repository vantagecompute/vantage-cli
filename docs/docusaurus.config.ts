import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';

const config: Config = {
  title: 'Vantage CLI',
  tagline: 'A powerful Python CLI for interacting with the Vantage platform',
  favicon: 'img/favicon.ico',

  url: 'https://vantagecompute.github.io',
  baseUrl: '/vantage-cli/',

  organizationName: 'vantagecompute',
  projectName: 'vantage-cli',
  deploymentBranch: 'main',
  trailingSlash: false,

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],

  presets: [
    [
      'classic',
      {
        docs: {
          path: './pages',
          routeBasePath: '/',
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/vantagecompute/vantage-cli/tree/main/docs/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      },
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'Vantage CLI Documentation',
      logo: {
        alt: 'Vantage Compute Logo',
        src: 'https://vantage-compute-public-assets.s3.us-east-1.amazonaws.com/branding/vantage-logo-text-white-horz.png',
        srcDark: 'https://vantage-compute-public-assets.s3.us-east-1.amazonaws.com/branding/vantage-logo-text-white-horz.png',
      },
      items: [
        {
          href: 'https://pypi.org/project/vantage-cli/',
          label: 'PyPI',
          position: 'right',
          className: 'pypi-button',
        },
        {
          href: 'https://github.com/vantagecompute/vantage-cli',
          label: 'GitHub',
          position: 'right',
          className: 'github-button',
        },
      ],
    },
    footer: {
      style: 'dark',
      logo: {
        alt: 'Vantage Compute Logo',
        src: 'https://vantage-compute-public-assets.s3.us-east-1.amazonaws.com/branding/vantage-logo-text-white-horz.png',
        href: 'https://vantagecompute.ai',
      },
      links: [
        {
          title: 'Documentation',
          items: [
            {
              label: 'Installation',
              to: '/installation',
            },
            {
              label: 'Usage Examples',
              to: '/usage',
            },
            {
              label: 'Commands',
              to: '/commands',
            },
          ],
        },

        {
          title: 'Community',
          items: [
            {
              label: 'GitHub Discussions',
              href: 'https://github.com/vantagecompute/vantage-cli/discussions',
            },
            {
              label: 'Issues',
              href: 'https://github.com/vantagecompute/vantage-cli/issues',
            },
            {
              label: 'Support',
              href: 'https://vantagecompute.ai/support',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/vantagecompute/vantage-cli',
            },
            {
              label: 'Vantage Compute',
              href: 'https://vantagecompute.ai',
            },
            {
              label: 'PyPI',
              href: 'https://pypi.org/project/vantage-cli/',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Vantage Compute.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
    tableOfContents: {
      minHeadingLevel: 2,
      maxHeadingLevel: 5,
    },
  },
};

export default config;
