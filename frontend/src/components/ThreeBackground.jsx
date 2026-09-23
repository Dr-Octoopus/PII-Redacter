import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function ThreeBackground({ theme = 'dark' }) {
  const containerRef = useRef(null);
  const themeRef = useRef(theme);

  useEffect(() => {
    themeRef.current = theme;
  }, [theme]);

  useEffect(() => {
    if (!containerRef.current) return;

    // 1. Scene, Camera, Renderer Setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      55,
      window.innerWidth / window.innerHeight,
      1,
      2000
    );
    camera.position.set(0, 0, 520);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    containerRef.current.appendChild(renderer.domElement);

    // 2. Color Palettes for Dark / Light Themes
    const palettes = {
      dark: {
        globeMesh: new THREE.Color(0x6366f1),     // Indigo
        globeInner: new THREE.Color(0x1e1b4b),    // Deep Navy
        ring: new THREE.Color(0x06b6d4),          // Cyan
        dots: new THREE.Color(0xc084fc),          // Purple
        particles: new THREE.Color(0x818cf8),     // Soft Indigo
        lines: new THREE.Color(0x38bdf8),        // Light Blue
        lineOpacity: 0.15,
      },
      light: {
        globeMesh: new THREE.Color(0x3b82f6),     // Blue
        globeInner: new THREE.Color(0xe0e7ff),    // Soft Blue Tint
        ring: new THREE.Color(0x8b5cf6),          // Violet
        dots: new THREE.Color(0xec4899),          // Pink
        particles: new THREE.Color(0x60a5fa),     // Light Blue
        lines: new THREE.Color(0xa78bfa),        // Light Violet
        lineOpacity: 0.1,
      },
    };

    let activePalette = themeRef.current === 'light' ? palettes.light : palettes.dark;

    // 3. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(activePalette.globeMesh.getHex(), 3, 1000);
    pointLight.position.set(250, 250, 350);
    scene.add(pointLight);

    // 4. Elegant 3D Digital Globe Group
    const globeGroup = new THREE.Group();

    // A. Outer Latitude/Longitude Wireframe Globe
    const globeRadius = 210;
    const globeGeo = new THREE.SphereGeometry(globeRadius, 36, 24);
    const globeMat = new THREE.MeshPhongMaterial({
      color: activePalette.globeMesh,
      wireframe: true,
      transparent: true,
      opacity: 0.22,
      shininess: 80,
    });
    const globeMesh = new THREE.Mesh(globeGeo, globeMat);
    globeGroup.add(globeMesh);

    // B. Inner Soft Atmosphere Core
    const innerGeo = new THREE.SphereGeometry(globeRadius - 6, 32, 32);
    const innerMat = new THREE.MeshBasicMaterial({
      color: activePalette.globeInner,
      transparent: true,
      opacity: 0.35,
    });
    const innerMesh = new THREE.Mesh(innerGeo, innerMat);
    globeGroup.add(innerMesh);

    // C. Orbiting Digital Equatorial Ring
    const ringGeo = new THREE.TorusGeometry(globeRadius + 45, 1.0, 16, 100);
    const ringMat = new THREE.MeshBasicMaterial({
      color: activePalette.ring,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = Math.PI / 2.8;
    globeGroup.add(ringMesh);

    // D. Outer Orbiting Satellite Ring
    const ring2Geo = new THREE.TorusGeometry(globeRadius + 85, 0.6, 12, 80);
    const ring2Mat = new THREE.MeshBasicMaterial({
      color: activePalette.dots,
      wireframe: true,
      transparent: true,
      opacity: 0.2,
    });
    const ring2Mesh = new THREE.Mesh(ring2Geo, ring2Mat);
    ring2Mesh.rotation.y = Math.PI / 3.5;
    globeGroup.add(ring2Mesh);

    // E. Surface Data Nodes (Points on Globe)
    const nodeCount = 120;
    const nodeGeo = new THREE.BufferGeometry();
    const nodePositions = new Float32Array(nodeCount * 3);

    for (let i = 0; i < nodeCount; i++) {
      const phi = Math.acos(-1 + (2 * i) / nodeCount);
      const theta = Math.sqrt(nodeCount * Math.PI) * phi;

      nodePositions[i * 3] = (globeRadius + 2) * Math.cos(theta) * Math.sin(phi);
      nodePositions[i * 3 + 1] = (globeRadius + 2) * Math.sin(theta) * Math.sin(phi);
      nodePositions[i * 3 + 2] = (globeRadius + 2) * Math.cos(phi);
    }

    nodeGeo.setAttribute('position', new THREE.BufferAttribute(nodePositions, 3));
    const nodeMat = new THREE.PointsMaterial({
      color: activePalette.dots,
      size: 4.5,
      transparent: true,
      opacity: 0.8,
    });
    const nodePoints = new THREE.Points(nodeGeo, nodeMat);
    globeGroup.add(nodePoints);

    scene.add(globeGroup);

    // 5. Subtle Ambient Background Particle Stream
    const particleCount = 160;
    const particleGeo = new THREE.BufferGeometry();
    const pPositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
      pPositions[i * 3] = (Math.random() - 0.5) * 1100;
      pPositions[i * 3 + 1] = (Math.random() - 0.5) * 800;
      pPositions[i * 3 + 2] = (Math.random() - 0.5) * 450;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(pPositions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: activePalette.particles,
      size: 3.5,
      transparent: true,
      opacity: 0.5,
    });
    const particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // 6. Smooth Mouse Parallax
    let mouseX = 0;
    let mouseY = 0;

    const handleMouseMove = (e) => {
      mouseX = (e.clientX - window.innerWidth / 2) * 0.15;
      mouseY = (e.clientY - window.innerHeight / 2) * 0.15;
    };

    window.addEventListener('mousemove', handleMouseMove);

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', handleResize);

    // 7. Silky Animation Loop
    let animationFrameId;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Theme Color Smooth Interpolation
      const targetPalette = themeRef.current === 'light' ? palettes.light : palettes.dark;
      globeMat.color.lerp(targetPalette.globeMesh, 0.05);
      innerMat.color.lerp(targetPalette.globeInner, 0.05);
      ringMat.color.lerp(targetPalette.ring, 0.05);
      ring2Mat.color.lerp(targetPalette.dots, 0.05);
      nodeMat.color.lerp(targetPalette.dots, 0.05);
      particleMat.color.lerp(targetPalette.particles, 0.05);
      pointLight.color.lerp(targetPalette.globeMesh, 0.05);

      // Smooth Globe Rotation
      globeMesh.rotation.y = elapsed * 0.08;
      globeMesh.rotation.x = Math.sin(elapsed * 0.04) * 0.05;

      ringMesh.rotation.z = elapsed * 0.12;
      ring2Mesh.rotation.z = -elapsed * 0.09;
      nodePoints.rotation.y = elapsed * 0.08;

      // Gentle Camera Parallax Follow
      camera.position.x += (mouseX - camera.position.x) * 0.03;
      camera.position.y += (-mouseY - camera.position.y) * 0.03;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
        overflow: 'hidden',
      }}
    />
  );
}
